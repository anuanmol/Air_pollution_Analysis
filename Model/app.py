import streamlit as st
import pickle 
import numpy as np 
import pandas as pd 
from datetime import datetime, timedelta
from fuzzywuzzy import process
import requests
import plotly.express as px
from copy import deepcopy
import json
import os 
from PIL import Image 
import time 

# import folium 

# set mapbox token
px.set_mapbox_access_token('pk.eyJ1IjoiYW5tb2w5IiwiYSI6ImNrczM2MWxmYzJhNm0zMnM3d25pZXJqcW0ifQ.e2XnfHzo0cEwS1pQemxH3w')



def validate_api(api):
    """
    Validates the API key by sending
    a single request to Climacell API
    :param api: 32-char API ket
    :return: True if api is valid
    """
    endpoint = "https://api.climacell.co/v3/weather/realtime"
    # Build sample params
    params = {'lat': '0', 'lon': '0', 'fields': 'temp',
              'apikey': str(api), 'unit_system': 'si'}
    # Get response
    response = requests.request('GET', endpoint, params=params)
    # If successful
    if response.status_code == 200:
        return True
    return False



def run_app():

    """
    A function to run
    the main part of the program
    """

    def load_data(path):
        """
        A function load data
        :param path: a path to the file source
        :return: pandas.DataFrame instance
        """
        df = pd.read_csv(path)
        return df

    def match_country(custom_input, df):
        """
        Match user input to available
        countries in the
        :param custom_input: text input for country
        :param df: main data
        :return: matching country as str
        """
        # Store unique country names
        unique_countries = set(df['country'].unique())
        # Find all matches for user_input
        match = process.extractOne(custom_input, unique_countries)
        # If similarity is over 70
        if match[1] >= 80:
            return match[0]
        else:
            return 'No match'

    def top25(df, country):
        """
        Subset for the top <25
        cities of the given country
        :param df: a dataset containing coords
                   for cities and countries
        :param country: a country matched from
                        user input
        :return: pandas.DataFrame containing
                 coords for top 25 cities
                 of given country
        """
        # Subset for cities of given country
        subset = df[df['country'] == country][['city_ascii', 'lat',
                                               'lng', 'population']]
        # Extract top 25 based on population size
        subset_sorted = subset.sort_values('population',
                                           ascending=False).iloc[:25]
        # Rename lng column to lon
        subset_sorted['lon'] = subset_sorted['lng']
        # Drop lng column
        subset_sorted.drop('lng', axis='columns', inplace=True)
        # Reorder columns
        subset_sorted = subset_sorted[['city_ascii', 'lat',
                                       'lon', 'population']]
        return subset_sorted.reset_index().drop('index', axis='columns')

    def call_api(cities_df, temp_unit):
        """
        Get current weather data
        for top25 cities from cities_df
        based on lat/lon
        :param temp_unit: value got from the user input radio btns
        :param cities_df: pandas.DataFrame with cities sorted by pop
        :return:
        """
        # Realtime endpoint
        weather_endpoint = "https://api.climacell.co/v3/weather/realtime"
        # Set the unit
        if temp_unit == '°C':
            temp_unit = 'si'
        else:
            temp_unit = 'us'
        # Query params
        params = {
            'unit_system': temp_unit,
            'fields': 'temp',
            # 'apikey': 'ke4PuUV8m6cepBeVZmfbe0gG7J3VdU2e',
            'apikey': '69GZYHnjqfMs3eQrnUDbWw0fbTck4S4l',
            'lat': '',
            'lon': ''
        }

        def call(row):
            """
            Function to return realtime temperature
            for each lat, lon
            """
            # Build querystring params
            params['lat'] = str(row['lat'])
            params['lon'] = str(row['lon'])
            # Make an API call
            response = requests.request("GET", weather_endpoint, params=params)
            if response.status_code == 200:
                response = json.loads(response.content)
                # Update row
                return round(float(response['temp']['value']), 1)
            else:
                response = '<400>'
                return response

        # Call for API for each row
        cities_df['Temperature'] = cities_df.apply(call, axis=1)
        # Create a column to resize the scatter plot dots
        cities_df['size'] = 15
        # Rename columns
        cities_df.rename(columns={'city_ascii': 'City'}, inplace=True)
        if 'population' in cities_df.columns:
            cities_df.drop('population', axis=True, inplace=True)
        # Check for status code
        if '<400>' in list(cities_df['Temperature']):
            return 400, None
        else:
            return 200, cities_df

    def map_plot(df, country):
        """
        A function to plot a scatter_mapbox
        of plotly
        :param country: a country input by user
        :param df: pandas.DataFrame containing temperature
                   and cities data
        :return: plotly figure
        """
        # Change the zoom level according to the shape of df
        size = df.shape[0]
        if size == 25:
            zoom = 3
        elif size == 20:
            zoom = 4
        else:
            zoom = 5
        # Get time for the moment
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Construct the figure
        fig = px.scatter_mapbox(df, hover_data=['Temperature', 'City'],
                                lat='lat', lon='lon',
                                color='Temperature', size='size',
                                color_continuous_scale=px.colors.cyclical.IceFire,
                                zoom=zoom)
        fig.update_traces(textposition='top center')
        fig.update_layout(title_text=f'Temperatures for {now}, {country.title()}', title_x=0.5)

        return fig

    def make_req(lat, lon, unit_system):
        """
        A vanilla function to make
        API call based on lat, lon
        """
        endpoint = "https://api.climacell.co/v3/weather/realtime"
        params = {
            'lat': lat, 'lon': lon,
            'fields': 'temp', 'unit_system': unit_system,
            # 'apikey': 'ke4PuUV8m6cepBeVZmfbe0gG7J3VdU2e'
            'apikey': '69GZYHnjqfMs3eQrnUDbWw0fbTck4S4l' 
        }
        res = requests.request("GET", endpoint, params=params)
        # If successful
        if res.status_code == 200:
            response = json.loads(res.content)
            # Build df
            df_dict = {
                'lat': [lat],
                'lon': [lon],
                'Temperature': [round(response['temp']['value'], 1)],
                'size': [15]
            }
            df = pd.DataFrame(df_dict, index=[0])
        else:  # set df to none if other status codes
            df = None
        return df, res.status_code

    def plot_single(df):
        """
        Vanilla function to
        plot scatter_mapbox based on single
        location
        """
        # Get time for the moment
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Construct the figure
        fig = px.scatter_mapbox(df, hover_data=['Temperature'],
                                lat='lat', lon='lon',
                                size='size',
                                color_continuous_scale=px.colors.cyclical.IceFire,
                                zoom=14)
        # Align text to the center
        fig.update_traces(textposition='top center')
        # Set title to the plot
        fig.update_layout(title_text=f'Temperatures for {now}, at ({df["lat"][0]},'
                                     f' {df["lon"][0]})', title_x=0.5)

        return fig

    # Load cities data with locations
    cities = load_data('dataall.csv')

    # Set a title
    st.title('')
    # Create radio options for location input
    st.subheader('Location:')
    action = st.radio('',
                      ['Coordinate(lati, long)', 'Enter Country Name', 'Choose Here'])
    unit = st.radio('Choose the unit for temperature:',
                    ['°C', '°F'])
    # Depending on action
    if action == 'Coordinate(lati, long)':
        # Create two columns to insert inputs side by side
        col1, col2 = st.beta_columns(2)
        with col1:  # latitude input
            latitude = st.text_input('Latitude (lat):')
        with col2:  # longitude input
            longitude = st.text_input('Longitude (lon):')
        # Leave instructions to get the coords
        
        # st.markdown('<small>If you don\'t know your coordinate '
        #             'location, go to <a href="https://www.latlong.net/">this</a> link. '
        #             '</small>',
        #             unsafe_allow_html=True)

        # If both fields are filled
        if latitude and longitude:
            # Call API and store as a single df
            temp_df, status_code = make_req(latitude, longitude, {'°C': 'si', '°F': 'us'}[unit])
            if status_code == 200:
                # Plot a single point
                plot = plot_single(temp_df)
                # Display dataframe too
                st.table(temp_df[['lat', 'lon', 'Temperature']])
                # Display as plotly chart
                st.plotly_chart(plot)
            elif status_code == 400:
                st.error('Invalid coordinates. Please try again!')
            else:
                st.error('Too many requests. Please try again in an hour...')

    elif action == 'Enter Country Name':
        user_input = st.text_input('Enter country (basic string matching '
                                   'is enabled under the hood):', max_chars=60)
        if user_input:
            # Match the input to existing countries
            country_input = match_country(user_input, cities)
            # If country matches
            if country_input != 'No match':
                # Inform the user about their option
                st.markdown(f"Matched **{country_input}**")
                # Create waiting event while getting temp data from API
                with st.spinner('Hang on... Fetching realtime temperatures...'):
                    # Subset for top <=25 cities of the country choice
                    top_cities = top25(cities, country_input)
                    # Store results of API call
                    status, temperatures = call_api(cities_df=top_cities, temp_unit=unit)
                # If request successful
                if status == 200:
                    # Show dataframe
                    st.dataframe(temperatures.drop('size', axis=1))  # TODO add a df toggler
                    # Create a waiting event while plotting
                    with st.spinner("Little more... Plotting the results..."):
                        # Inform the user to hover over points
                        st.subheader('Hover over the points and drag around to see temperatures')
                        # Display the plotly chart using returned data
                        st.plotly_chart(map_plot(top_cities, country_input))
                else:  # if status code != 200, it means too many requests
                    st.error('Too many requests. Please try again in an hour')
            else:  # if country_input == 'No match'
                st.error('Could not find a match from the database. Try again...')

    else:  # If user chooses to input via dropdown
        # Create a dropdown
        country_input = st.selectbox('Choose country',
                                     sorted([''] + list(cities['country'].unique())))
        # If user choose a country from dropdown
        if country_input:
            # Inform the user about their option
            st.markdown(f"You chose **{country_input}**")
            # Create waiting event while getting temp data from API
            with st.spinner('Getting realtime temperatures...'):
                # Subset for top <=25 cities of the country choice
                top_cities = top25(cities, country_input)
                # Store results of API call
                status, temperatures = call_api(cities_df=top_cities, temp_unit=unit)
            # If request successful
            if status == 200:
                # Show dataframe
                st.dataframe(temperatures.drop('size', axis=1))  # TODO add a df toggler
                # Create a waiting event while plotting
                with st.spinner("Little more... Plotting the results..."):
                    # Inform the user to hover over points
                    st.subheader('Hover over the points to see temperatures')
                    # Display the plotly chart using returned data
                    st.plotly_chart(map_plot(top_cities, country_input))
            else:  # if status code != 200, it means too many requests
                st.error('Too many requests. Please try again in an hour')




def main():
    st.markdown('''<center><h1><b>AQI</b></center></h1>''', unsafe_allow_html=True)
    # st.header("AQI")
    name = "modelall.sav"
    model = pickle.load(open('modelall.sav','rb'))

    # st.markdown('''<center><img src="https://user-images.githubusercontent.com/51512071/128558138-0b069fe8-71ac-4a68-8877-4690e6937f0f.png"></center><br><hr>''', unsafe_allow_html=True)

    st.markdown('''<br>''', unsafe_allow_html=True)

    ch = st.selectbox("",['--select--','About','Study','Live'])
    st.markdown('''<br>''', unsafe_allow_html=True)

    if ch == '--select--':

        st.markdown("<center><img src='https://user-images.githubusercontent.com/51512071/128558576-8290e14f-450d-42c0-b8ab-b036e117c9ac.png'></center>", unsafe_allow_html=True)

        st.markdown('''''')

    if ch == 'Live':
        run_app()


    if ch == 'Predict':
        st.subheader("PM2.5")
        pm25 = st.number_input("", key=1)
        pm10 = st.number_input("", key=2)
        co = st.number_input("", key=3)
        no = st.number_input("", key=4)
        so = st.number_input("", key=5)
        nox = st.number_input("", key=6)


        p = model.predict([[25, 35, 95, 100, 50, 78, 55, 15, 10, 5]])
        st.write(p)

    if ch == 'Study':
        pass


if __name__ == "__main__":
    main()