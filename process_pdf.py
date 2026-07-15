import os
import re
import math
import urllib.request
import urllib.parse
import json
import csv
import time

# Constants
START_ADDRESS = "2505 Dean Lesher Dr, Concord, CA"
START_LAT = 38.0205834
START_LON = -122.0306097

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # radius of Earth in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def geocode_census(query):
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=" + urllib.parse.quote(query) + "&benchmark=Public_AR_Current&format=json"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            matches = data.get("result", {}).get("addressMatches", [])
            results = []
            for m in matches:
                lat = m.get("coordinates", {}).get("y")
                lon = m.get("coordinates", {}).get("x")
                matched_addr = m.get("matchedAddress", "")
                
                # Geocode filter: reject matches that are more than 30 miles from our Concord starting depot.
                # This prevents matching duplicate street names in far-away counties.
                if lat is not None and lon is not None:
                    dist = haversine(START_LAT, START_LON, lat, lon)
                    if dist > 30.0:
                        print(f"  Ignored far-away geocode match ({dist:.1f} mi): {matched_addr}")
                        continue
                
                parts = [p.strip() for p in matched_addr.split(",")]
                city = None
                if len(parts) >= 3:
                    city = parts[-3]
                results.append({"lat": lat, "lon": lon, "matched": matched_addr, "city": city})
            return results
    except Exception as e:
        print(f"Error geocoding '{query}': {e}")
        return []

def extract_pdf_data(pdf_path):
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    
    current_route = None
    current_street = None
    deliveries = []
    
    for page in reader.pages:
        text = page.extract_text()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("--- PAGE"):
                continue
            if line.startswith("Route:"):
                current_route = line.split("Route:")[1].split("-")[0].strip()
                continue
            if line.startswith("Delivery for"):
                continue
            
            m = re.match(r"^(\d+)\s+([A-Z]{2,4})\s+([A-Z0-9]+)\s+(\d+)$", line)
            if m:
                num = m.group(1)
                paper = m.group(2)
                if current_street:
                    deliveries.append({
                        "route": current_route,
                        "street": current_street,
                        "number": num,
                        "paper": paper
                    })
            else:
                current_street = line
                
    # Group by unique address
    grouped = {}
    for d in deliveries:
        addr = f"{d['number']} {d['street']}"
        if addr not in grouped:
            grouped[addr] = {
                "route": d["route"],
                "number": d["number"],
                "street": d["street"],
                "papers": set()
            }
        grouped[addr]["papers"].add(d["paper"])
        
    return grouped

def geocode_addresses(grouped_data):
    # Group addresses by route for majority city calculation
    routes_addrs = {}
    for addr, data in grouped_data.items():
        r_id = data["route"]
        if r_id not in routes_addrs:
            routes_addrs[r_id] = []
        routes_addrs[r_id].append((addr, data))
        
    resolved = {}
    
    for r_id, items in routes_addrs.items():
        print(f"Geocoding Route {r_id} ({len(items)} addresses)...")
        single_matches = []
        ambiguous_matches = []
        unmatched = []
        
        for addr, data in items:
            query = f"{data['number']} {data['street']}, CA"
            matches = geocode_census(query)
            time.sleep(0.1) # short delay
            
            if len(matches) == 1:
                m = matches[0]
                data["lat"] = m["lat"]
                data["lon"] = m["lon"]
                data["city"] = m["city"]
                single_matches.append((addr, data))
            elif len(matches) > 1:
                ambiguous_matches.append((addr, data, matches))
            else:
                unmatched.append((addr, data))
                
        # Majority city
        cities = [d["city"] for a, d in single_matches if d.get("city")]
        majority_city = max(set(cities), key=cities.count) if cities else "WALNUT CREEK"
        print(f"  Majority City: {majority_city}")
        
        # Resolve ambiguous
        for addr, data, matches in ambiguous_matches:
            best_match = None
            for m in matches:
                if m["city"] and m["city"].upper() == majority_city.upper():
                    best_match = m
                    break
            if not best_match:
                best_match = matches[0]
            data["lat"] = best_match["lat"]
            data["lon"] = best_match["lon"]
            data["city"] = best_match["city"]
            single_matches.append((addr, data))
            
        # Resolve unmatched
        for addr, data in unmatched:
            query = f"{data['number']} {data['street']}, {majority_city}, CA"
            matches = geocode_census(query)
            time.sleep(0.1)
            if matches:
                m = matches[0]
                data["lat"] = m["lat"]
                data["lon"] = m["lon"]
                data["city"] = majority_city
                single_matches.append((addr, data))
            else:
                # Try street name only
                query_street = f"{data['street']}, {majority_city}, CA"
                matches_street = geocode_census(query_street)
                time.sleep(0.1)
                if matches_street:
                    m = matches_street[0]
                    data["lat"] = m["lat"]
                    data["lon"] = m["lon"]
                    data["city"] = majority_city
                    single_matches.append((addr, data))
                else:
                    # Fallback placeholder (will be filled with a neighbor's coords below)
                    data["lat"] = None
                    data["lon"] = None
                    data["city"] = majority_city
                    single_matches.append((addr, data))
                    
        # Apply neighborhood fallbacks for missing coords in the route
        valid_coords = [(d["lat"], d["lon"]) for a, d in single_matches if d["lat"] is not None]
        fallback_coord = valid_coords[0] if valid_coords else (START_LAT, START_LON)
        
        for addr, data in single_matches:
            if data["lat"] is None:
                data["lat"], data["lon"] = fallback_coord
                print(f"  Using route fallback coords for unmatched address: {addr}")
            resolved[addr] = data
            
    return resolved

def solve_tsp(addresses_dict):
    # Create the list of points to optimize
    # Pinned first element
    points = [{
        "address": START_ADDRESS,
        "lat": START_LAT,
        "lon": START_LON,
        "papers": "",
        "city": "Concord"
    }]
    
    for addr, data in addresses_dict.items():
        # Capitalize street and city in title case for real-life sign representation
        street_title = data['street'].strip().title()
        city_title = data['city'].strip().title()
        
        points.append({
            "address": f"{data['number']} {street_title}, {city_title}, CA",
            "lat": data["lat"],
            "lon": data["lon"],
            "papers": " ".join(sorted(data["papers"])),
            "city": city_title
        })
        
    N = len(points)
    print(f"Optimizing route for {N} waypoints...")
    
    # 1. Nearest Neighbor (preserving index 0)
    unvisited = set(range(1, N))
    tour = [0]
    while unvisited:
        last = tour[-1]
        nxt = min(unvisited, key=lambda i: haversine(
            points[last]["lat"], points[last]["lon"],
            points[i]["lat"], points[i]["lon"]
        ))
        tour.append(nxt)
        unvisited.remove(nxt)
        
    # Helper to calculate route length
    def get_tour_length(t):
        return sum(haversine(
            points[t[i]]["lat"], points[t[i]]["lon"],
            points[t[i+1]]["lat"], points[t[i+1]]["lon"]
        ) for i in range(len(t) - 1))
        
    # 2. 2-opt optimization (preserving start index 0)
    improved = True
    best_tour = tour[:]
    best_len = get_tour_length(best_tour)
    
    while improved:
        improved = False
        # Only swap indices >= 1 to preserve start address at index 0
        for i in range(1, N - 2):
            for j in range(i + 1, N - 1):
                # Reverse segment between i and j
                new_tour = best_tour[:i] + best_tour[i:j+1][::-1] + best_tour[j+1:]
                new_len = get_tour_length(new_tour)
                if new_len < best_len:
                    best_tour = new_tour
                    best_len = new_len
                    improved = True
                    
    print(f"Optimized route total open path distance: {best_len:.2f} miles")
    return [points[idx] for idx in best_tour]

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(workspace, "MyDistrictNet.pdf")
    csv_dir = os.path.join(workspace, "csv")
    chapters_csv = os.path.join(csv_dir, "Chapters.csv")
    
    # Read existing CSV for metadata preservation (using case-insensitive comparison)
    existing_meta = {}
    if os.path.exists(chapters_csv):
        with open(chapters_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row["Chapter"].split(",")[0].strip().upper()
                existing_meta[addr] = row
                
    # Extract PDF
    print("Extracting PDF data...")
    raw_data = extract_pdf_data(pdf_path)
    print(f"Extracted {len(raw_data)} unique delivery addresses.")
    
    # Geocode
    print("Geocoding addresses...")
    geocoded_data = geocode_addresses(raw_data)
    
    # TSP Optimization
    print("Optimizing route...")
    optimized_route = solve_tsp(geocoded_data)
    
    # Write new CSV
    print("Writing new Chapters.csv...")
    fieldnames = [
        "Chapter", "Media Link", "Media Credit", "Media Credit Link", 
        "Description", "Zoom", "Marker", "Marker Color", "Location", 
        "Latitude", "Longitude", "Overlay", "Overlay Transparency", 
        "GeoJSON Overlay", "GeoJSON Feature Properties", "Newspapers", "Maps Link"
    ]
    
    os.makedirs(csv_dir, exist_ok=True)
    with open(chapters_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, pt in enumerate(optimized_route):
            addr_key = pt["address"].split(",")[0].strip().upper()
            meta = existing_meta.get(addr_key, {})
            
            # Format maps link
            maps_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(pt['address'])}"
            
            # Carry over metadata
            row_data = {
                "Chapter": pt["address"],
                "Media Link": meta.get("Media Link", ""),
                "Media Credit": "Open in Maps",
                "Media Credit Link": maps_link if i == 0 else meta.get("Media Credit Link", maps_link),
                "Description": meta.get("Description", "Start Address" if i == 0 else ""),
                "Zoom": meta.get("Zoom", "16"),
                "Marker": meta.get("Marker", "Numbered"),
                "Marker Color": meta.get("Marker Color", "blue" if i > 0 else "red"),
                "Location": meta.get("Location", ""),
                "Latitude": pt["lat"],
                "Longitude": pt["lon"],
                "Overlay": meta.get("Overlay", ""),
                "Overlay Transparency": meta.get("Overlay Transparency", ""),
                "GeoJSON Overlay": meta.get("GeoJSON Overlay", ""),
                "GeoJSON Feature Properties": meta.get("GeoJSON Feature Properties", ""),
                "Newspapers": pt["papers"],
                "Maps Link": maps_link
            }
            writer.writerow(row_data)
            
    print("Chapters.csv successfully written!")

if __name__ == "__main__":
    main()
