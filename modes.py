import googlemaps
import requests
from flask import current_app

class GoogleMapsService:
    def __init__(self, api_key):
        self.client = googlemaps.Client(key=api_key)
        self.api_key = api_key
    
    def geocode_address(self, address):
        """
        Convert address to coordinates
        """
        try:
            geocode_result = self.client.geocode(address)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                formatted_address = geocode_result[0]['formatted_address']
                return {
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'formatted_address': formatted_address,
                    'success': True
                }
            return {'success': False, 'error': 'Address not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def find_nearby_mechanics(self, latitude, longitude, radius=5000):
        """
        Find nearby mechanics and tire shops
        radius in meters (5000m = ~3 miles)
        """
        try:
            # Search for auto repair shops
            places_result = self.client.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                type='car_repair'
            )
            
            # Also search for tire shops
            tire_shops = self.client.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                keyword='tire shop'
            )
            
            # Combine results
            all_places = places_result.get('results', []) + tire_shops.get('results', [])
            
            # Process and return relevant information
            mechanics = []
            for place in all_places:
                mechanic_info = {
                    'name': place.get('name', 'Unknown'),
                    'address': place.get('vicinity', 'Address not available'),
                    'rating': place.get('rating', 0),
                    'price_level': place.get('price_level', 'N/A'),
                    'place_id': place.get('place_id'),
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'types': place.get('types', []),
                    'open_now': place.get('opening_hours', {}).get('open_now', None)
                }
                mechanics.append(mechanic_info)
            
            # Sort by rating (highest first)
            mechanics.sort(key=lambda x: x['rating'], reverse=True)
            
            return {
                'success': True,
                'mechanics': mechanics[:10]  # Return top 10
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_place_details(self, place_id):
        """
        Get detailed information about a specific place
        """
        try:
            place_details = self.client.place(
                place_id=place_id,
                fields=['name', 'formatted_address', 'formatted_phone_number', 
                       'website', 'opening_hours', 'rating', 'reviews']
            )
            return {
                'success': True,
                'details': place_details['result']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def calculate_distance(self, origin_lat, origin_lng, dest_lat, dest_lng):
        """
        Calculate distance between two points
        """
        try:
            distance_result = self.client.distance_matrix(
                origins=[(origin_lat, origin_lng)],
                destinations=[(dest_lat, dest_lng)],
                mode="driving",
                units="metric"
            )
            
            if distance_result['rows'][0]['elements'][0]['status'] == 'OK':
                distance = distance_result['rows'][0]['elements'][0]['distance']['text']
                duration = distance_result['rows'][0]['elements'][0]['duration']['text']
                return {
                    'success': True,
                    'distance': distance,
                    'duration': duration
                }
            return {'success': False, 'error': 'Could not calculate distance'}
        except Exception as e:
            return {'success': False, 'error': str(e)}