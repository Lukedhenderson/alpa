import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import ee
from google.oauth2 import service_account
import json
from chat import chat_with_gpt

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize Earth Engine
def initialize_ee():
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/earthengine.readonly']
    )
    ee.Initialize(credentials)

initialize_ee()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        prompt = data.get('message', '')
        response_text = chat_with_gpt(prompt)
        return jsonify({'response': response_text})
    except Exception as e:
        print(f"Error in /chat: {str(e)}")
        return jsonify({'response': "An error occurred"}), 500

@app.route('/app/index')
def index():
    return render_template('index.html')

@app.route('/app/results', methods=['POST'])
def results():
    try:
        aoi_geojson = request.form['aoi']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        aoi = ee.Geometry.Polygon(json.loads(aoi_geojson)['coordinates'])

        # Calculate vegetation indices
        ndvi, evi = calculate_vegetation_indices(aoi, start_date, end_date)
        ndvi_url = ndvi.getThumbURL({
            'min': 0,
            'max': 1,
            'palette': ['blue', 'green', 'red'],
            'region': aoi,
            'dimensions': 512
        })
        evi_url = evi.getThumbURL({
            'min': 0,
            'max': 1,
            'palette': ['blue', 'green', 'red'],
            'region': aoi,
            'dimensions': 512
        })

        # Estimate soil moisture
        soil_moisture = estimate_soil_moisture(aoi, start_date, end_date)
        soil_moisture_url = None
        if soil_moisture:
            soil_moisture_url = soil_moisture.getThumbURL({
                'min': -25,
                'max': 0,
                'palette': ['blue', 'green', 'yellow', 'red'],
                'region': aoi,
                'dimensions': 512
            })

        # Get true color image
        true_color = get_true_color_image(aoi, start_date, end_date)
        true_color_url = true_color.getThumbURL({
            'region': aoi,
            'dimensions': 512
        })

        # Track crop growth and predict yield
        yield_pred, growth_stage = track_crop_growth_and_predict_yield(aoi, start_date, end_date)
        yield_pred_url = yield_pred.getThumbURL({
            'min': 0,
            'max': 100,
            'palette': ['blue', 'green', 'yellow', 'red'],
            'region': aoi,
            'dimensions': 512
        })

        return render_template('results.html', ndvi_url=ndvi_url, evi_url=evi_url, soil_moisture_url=soil_moisture_url, true_color_url=true_color_url, yield_info=yield_pred_url, growth_stage=growth_stage)

    except ValueError as ve:
        print(f"Value Error in /app/results: {str(ve)}")
        return render_template('error.html', message="Invalid input values. Please check your coordinates and dates."), 400

    except ee.EEException as eee:
        print(f"Earth Engine Error in /app/results: {str(eee)}")
        return render_template('error.html', message="Error processing Earth Engine request. Please try again later."), 500

    except Exception as e:
        print(f"General Error in /app/results: {str(e)}")
        return render_template('error.html', message="An unexpected error occurred. Please try again later."), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Function to calculate vegetation indices
def calculate_vegetation_indices(aoi, start_date, end_date):
    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR') \
                  .filterDate(start_date, end_date) \
                  .filterBounds(aoi) \
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))

    ndvi = sentinel2.map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI')).median().clip(aoi)
    evi = sentinel2.map(lambda img: img.expression(
        '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
            'NIR': img.select('B8'),
            'RED': img.select('B4'),
            'BLUE': img.select('B2')
        }).rename('EVI')).median().clip(aoi)

    return ndvi, evi

def estimate_soil_moisture(aoi, start_date, end_date):
    try:
        sentinel1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
                      .filterDate(start_date, end_date) \
                      .filterBounds(aoi) \
                      .filter(ee.Filter.eq('instrumentMode', 'IW')) \
                      .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')) \
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
                      .select('VV')

        if sentinel1.size().getInfo() == 0:
            print("No Sentinel-1 GRD images found for the specified AOI and date range.")
            return None

        soil_moisture = sentinel1.mean().clip(aoi).rename('Soil_Moisture')
        return soil_moisture
    except Exception as e:
        print(f"Error in estimate_soil_moisture: {str(e)}")
        return None

# Function to get true color image
def get_true_color_image(aoi, start_date, end_date):
    sentinel2 = ee.ImageCollection('COPERNICUS/S2') \
                  .filterDate(start_date, end_date) \
                  .filterBounds(aoi) \
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
                  .filter(ee.Filter.listContains('system:band_names', 'B2'))

    def mask_cloud_and_shadows(image):
        cloud_mask = image.select('QA60').bitwiseAnd(1 << 10).eq(0)
        cirrus_mask = image.select('QA60').bitwiseAnd(1 << 11).eq(0)
        return image.updateMask(cloud_mask).updateMask(cirrus_mask)

    true_color = sentinel2.map(mask_cloud_and_shadows).select(['B4', 'B3', 'B2']).median().clip(aoi).visualize(min=0, max=3000)
    return true_color

# Function to track crop growth and predict yield
def track_crop_growth_and_predict_yield(aoi, start_date, end_date):
    ndvi = ee.ImageCollection('COPERNICUS/S2_SR') \
              .filterDate(start_date, end_date) \
              .filterBounds(aoi) \
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
              .map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI')).median().clip(aoi)
    
    yield_prediction = ndvi.multiply(100)
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    
    mean_ndvi = stats.get('NDVI', None)
    growth_stage = "Unknown"
    
    if mean_ndvi is not None:
        if mean_ndvi < 0.2:
            growth_stage = "Early Growth Stage"
        elif 0.2 <= mean_ndvi < 0.5:
            growth_stage = "Mid Growth Stage"
        elif mean_ndvi >= 0.5:
            growth_stage = "Late Growth Stage"
    
    return yield_prediction, growth_stage

if __name__ == '__main__':
    app.run(debug=False)