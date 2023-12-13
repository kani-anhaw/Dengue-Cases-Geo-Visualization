from django.shortcuts import render
import geopandas as gpd
import folium
import pandas as pd
from .models import Final

def analytics(request):
    geojson_file = r'C:\Users\felom\OneDrive\Desktop\New folder\highres.json'
    gdf = gpd.read_file(geojson_file)

    model_data = Final.objects.all()

    df = pd.DataFrame(list(model_data.values()))

    # Aggregate cases per region
    cases_by_region = df.groupby('region')['cases'].sum().reset_index()

    # Merge aggregated data with GeoDataFrame
    merged_data = pd.merge(gdf, cases_by_region, left_on='REGION', right_on='region', how='left')

    # Create a Folium map
    m = folium.Map(location=[12.8797, 121.7740], zoom_start=6)

    # Add choropleth layer using GeoDataFrame
    choropleth_layer = folium.Choropleth(
        geo_data=merged_data,
        data=merged_data,
        columns=['region', 'cases'],
        key_on='feature.properties.REGION',
        fill_color='YlGn',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Total Cases',
    ).add_to(m)

    folium.GeoJson(
        merged_data,
        tooltip=folium.GeoJsonTooltip(fields=['REGION'], localize=True),
    ).add_to(m)


    # Save the map to an HTML file
    map_html = m.get_root().render()

    # Pass the Folium map HTML to the template
    context = {'map_html': map_html}    
    return render(request, 'final/analytics.html', context)

# def get_cached_data():
#     geojson_file = r'C:\Users\felom\OneDrive\Desktop\New folder\lowres.json'
#     gdf = cache.get('gdf')
#     if not gdf:
#         gdf = gpd.read_file(geojson_file)
#         cache.set('gdf', gdf, timeout=None)  # Cache forever

#     model_data = cache.get('model_data')
#     if not model_data:
#         model_data = list(Final.objects.all().values())
#         cache.set('model_data', model_data, timeout=None)

#     return gdf, model_data

# def generate_folium_map():
#     gdf, model_data = get_cached_data()

#     df = pd.DataFrame(model_data)
#     merged_data = pd.merge(gdf, df, left_on='REGION', right_on='region', how='left')

#     m = folium.Map(location=[12.8797, 121.7740], zoom_start=6)

#     # Add choropleth layer using GeoDataFrame
#     choropleth_layer = folium.Choropleth(
#         geo_data=merged_data,
#         data=merged_data,
#         columns=['region', 'cases'],
#         key_on='feature.properties.REGION',
#         fill_color='YlGn',
#         fill_opacity=0.7,
#         line_opacity=0.2,
#         legend_name='Population',
#     ).add_to(m)

#     # Add red lines on the boundaries using GeoJson layer
#     folium.GeoJson(
#         merged_data,
#         tooltip=folium.GeoJsonTooltip(fields=['REGION'], localize=True),
#     ).add_to(m)


#     map_html = m.get_root().render()
#     return map_html
