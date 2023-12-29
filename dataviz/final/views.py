from django.shortcuts import render
from .models import Final
import plotly.express as px
import folium
from django.db.models import Sum
import geopandas as gpd
import pandas as pd
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import HttpResponseBadRequest
from django.db.models import Sum, Q


def format_total(n):
    n = float(n)
    if n >= 1e9:
        return f"{n / 1e9:.1f}B"
    elif n >= 1e6:
        return f"{n / 1e6:.1f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.1f}K"
    elif n >= 100:
        return f"{int(n)}"
    else:
        return str(n)


def index(request):
    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Filter data based on the search query
    filtered_data = Final.objects.filter(
        Q(city__icontains=search_query) | Q(region__icontains=search_query)
    ).values('city', 'region').annotate(
        total_cases=Sum('cases'),
        total_deaths=Sum('deaths')
    )

    # Calculate total_case, total_deaths, and cfr from the filtered data
    total_case = sum(item['total_cases'] for item in filtered_data)
    total_deaths = sum(item['total_deaths'] for item in filtered_data)

    cfr = (total_deaths / total_case) * 100 if total_case > 0 else 0
    formatted_cfr = round(cfr, 2)

    # Format total_case and total_deaths using the format_total function
    formatted_total_case = format_total(total_case)
    formatted_total_deaths = format_total(total_deaths)

    # Convert CFR into a colon ratio
    # if total_case > 0:
    #     equivalent_left_side = (100 / (100 - cfr)) * total_deaths
    #     colon_ratio = f'{int(equivalent_left_side)}:{total_case}'
    # else:
    #     colon_ratio = '0:0'

    # Number of items to display per page
    items_per_page = 4
    paginator = Paginator(filtered_data, items_per_page)

    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page.
        items = paginator.page(1)
    except EmptyPage:
        # If the page is out of range (e.g., 9999), deliver the last page of results.
        items = paginator.page(paginator.num_pages)

    context = {
        'items': items,
        'total_case': formatted_total_case,
        'total_death': formatted_total_deaths,
        'cfr': formatted_cfr,  # Add the colon ratio to the context
        'search_query': search_query,  # Add the search query to the context
    }

    return render(request, 'final/index.html', context)



# sem-final
def others(request):

    
    geojson_file = r'C:\Users\felom\Documents\ITD112\final\New folder\midres.json'
    gdf = gpd.read_file(geojson_file)

    model_data = Final.objects.all()

    df = pd.DataFrame(list(model_data.values()))

    cases_by_region = df.groupby('region')['cases'].sum().reset_index()
    merged_data = pd.merge(gdf, cases_by_region, left_on='REGION', right_on='region', how='left')

    m = folium.Map(location=[12.8797, 121.7740], zoom_start=6)


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
        tooltip=folium.GeoJsonTooltip(fields=['REGION', 'cases'], aliases=['Region', 'Cases'], localize=True),
    ).add_to(m)

  
    map_html = m.get_root().render()
    context = {'map_html': map_html}    
    return render(request, 'final/others.html', context)



def analytics(request):
    geojson_file = r'C:\Users\felom\Documents\ITD112\final\New folder\midres.json'
    gdf = gpd.read_file(geojson_file)

    model_data = Final.objects.all()

    df = pd.DataFrame(list(model_data.values()))

    # Map month numbers to month names
    month_mapping = {
        1: 'Jan',
        2: 'Feb',
        3: 'Mar',
        4: 'Apr',
        5: 'May',
        6: 'Jun',
        7: 'Jul',
        8: 'Aug',
        9: 'Sep',
        10: 'Oct',
        11: 'Nov',
        12: 'Dec'
    }
    df['month'] = df['month'].map(month_mapping)

    # Get the selected time unit from the request (default to 'year' if not specified)
    time_unit = request.GET.get('time_unit', 'year')

    # Ensure months are in the correct order
    df['month'] = pd.Categorical(df['month'], categories=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], ordered=True)

    # Choropleth Map
    if time_unit == 'year':
        cases_by_region_time = df.groupby(['region', 'year'])['cases'].sum().reset_index()
        animation_frame_col = 'year'
    elif time_unit == 'month':
        cases_by_region_time = df.groupby(['region', 'month'])['cases'].sum().reset_index()
        animation_frame_col = 'month'
    else:
        return HttpResponseBadRequest("Invalid time unit selected")

    merged_data = pd.merge(gdf, cases_by_region_time, left_on='REGION', right_on='region', how='left')

    fig_choropleth = px.choropleth(
        merged_data,
        geojson=merged_data.geometry,
        locations=merged_data.index,
        color='cases',
        hover_name='REGION',
        animation_frame=animation_frame_col,
        color_continuous_scale="Reds",
    )

    fig_choropleth.update_geos(center=dict(lon=121, lat=13), projection_scale=20)
    fig_choropleth.update_layout(width=600, autosize=False, margin=dict(l=10, r=10, b=10, t=50, pad=1))

    choropleth_html = fig_choropleth.to_html(full_html=False)

    # Line Graph
    cases_by_time = df.groupby([animation_frame_col])['cases'].sum().reset_index()

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=cases_by_time[animation_frame_col], y=cases_by_time['cases'], mode='lines+markers'))

    if time_unit == 'year':
        title = 'Cases Over Years'
        xaxis_title = 'Year'
    elif time_unit == 'month':
        title = 'Cases Over Months'
        xaxis_title = 'Month'

    fig_line.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title='Cases',
        width=350,
        height=325,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    line_html = fig_line.to_html(full_html=False)

    max_cases_region_row = cases_by_region_time.loc[cases_by_region_time['cases'].idxmax()]
    min_cases_region_row = cases_by_region_time.loc[cases_by_region_time['cases'].idxmin()]

    max_cases_region = max_cases_region_row['region']
    min_cases_region = min_cases_region_row['region']

    sum_cases_max_region = max_cases_region_row['cases']
    sum_cases_min_region = min_cases_region_row['cases']

    additional_info = {
        'max_cases_region': max_cases_region,
        'min_cases_region': min_cases_region,
        'sum_cases_max_region': sum_cases_max_region,
        'sum_cases_min_region': sum_cases_min_region,
    }

    context = {'choropleth_html': choropleth_html, 'line_html': line_html, 'additional_info': additional_info}
    return render(request, 'final/analytics.html', context)


def bubble_map(request):
    model_data = Final.objects.all()
    df = pd.DataFrame(list(model_data.values()))

    month_mapping = {
        1: 'Jan',
        2: 'Feb',
        3: 'Mar',
        4: 'Apr',
        5: 'May',
        6: 'Jun',
        7: 'Jul',
        8: 'Aug',
        9: 'Sep',
        10: 'Oct',
        11: 'Nov',
        12: 'Dec'
    }
    df['month'] = df['month'].map(month_mapping)
    deaths_by_city = df.groupby(['city', 'latitude', 'longitude', 'month', 'year'])['deaths'].sum().reset_index()

    # Set 'year' as the default time unit
    time_unit = request.GET.get('time_unit', 'year')
     # Ensure months are in the correct order
    df['month'] = pd.Categorical(df['month'], categories=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], ordered=True)

    # Choropleth Map
    if time_unit == 'year':
        deaths_by_region_time = df.groupby(['region', 'year'])['deaths'].sum().reset_index()
        animation_frame_col = 'year'
    elif time_unit == 'month':
        deaths_by_region_time = df.groupby(['region', 'month'])['deaths'].sum().reset_index()
        animation_frame_col = 'month'
    else:
        return HttpResponseBadRequest("Invalid time unit selected")

    # Bubble Map
    fig = px.scatter_geo(
        deaths_by_city,
        lat='latitude',
        lon='longitude',
        color='deaths',
        size='deaths',
        hover_name='city',
        animation_frame=animation_frame_col,
        projection='mercator',
        category_orders={'month': list(month_mapping.values())},
        color_continuous_scale='Reds', 
    )

    fig.update_geos(center=dict(lon=121, lat=13), 
                    resolution=50,
                    showocean=True, oceancolor="LightBlue",
                    projection_scale=25)
    fig.update_layout(width=600,
                      height=600,
                      autosize=False,
                      margin=dict(l=10, r=10, b=10, t=50, pad=1))

    bubble_map_html = fig.to_html(full_html=False)

   # Bar Graph
    deaths_by_time = df.groupby([animation_frame_col])['deaths'].sum().reset_index()
    bar_fig = px.bar(deaths_by_time, x=animation_frame_col, y='deaths', labels={'deaths': 'Total Deaths'})

    if time_unit == 'year':
        title = 'Total Deaths by Year'
    elif time_unit == 'month':
        title = 'Total Deaths by Month'

    bar_fig.update_layout(
        title=title,
        xaxis_title=animation_frame_col.capitalize(),
        yaxis_title='Total Deaths',
        width=350,
        height=450,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    bar_graph_html = bar_fig.to_html(full_html=False)

    month_with_least_deaths = deaths_by_time.loc[deaths_by_time['deaths'].idxmin()][animation_frame_col]
    month_with_most_deaths = deaths_by_time.loc[deaths_by_time['deaths'].idxmax()][animation_frame_col]

    total_least_deaths = deaths_by_time['deaths'].min()
    total_most_deaths = deaths_by_time['deaths'].max()


    context = {
        'bubble_map_html': bubble_map_html,
        'bar_graph_html': bar_graph_html,
        'month_with_least_deaths': month_with_least_deaths,
        'month_with_most_deaths': month_with_most_deaths,
        'total_least_deaths': total_least_deaths,
        'total_most_deaths': total_most_deaths,
    }
    return render(request, 'final/bubbleMap.html', context)

