import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
import ee
from google.oauth2 import service_account

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/')
def landing():
    print("Landing page accessed")
    return render_template('landing.html')

@app.route('/app/index')
def index():
    print("Index page accessed")
    return render_template('index.html')

@app.route('/app/results', methods=['POST'])
def results():
    try:
        lat1 = float(request.form['lat1'])
        lon1 = float(request.form['lon1'])
        lat2 = float(request.form['lat2'])
        lon2 = float(request.form['lon2'])
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        aoi = ee.Geometry.Rectangle([lon1, lat1, lon2, lat2])

        print(f"Received AOI: {aoi.getInfo()}, Start Date: {start_date}, End Date: {end_date}")

        # Calculate vegetation indices
        ndvi, evi = calculate_vegetation_indices(aoi, start_date, end_date)
        ndvi_url = ndvi.getThumbURL({
            'min': 0, 
            'max': 1, 
            'palette': ['blue', 'green', 'red'], 
            'region': aoi.toGeoJSONString(),
            'dimensions': 512
        })
        evi_url = evi.getThumbURL({
            'min': 0, 
            'max': 1, 
            'palette': ['blue', 'green', 'red'], 
            'region': aoi.toGeoJSONString(),
            'dimensions': 512
        })

        print(f"NDVI URL: {ndvi_url}, EVI URL: {evi_url}")

        # Estimate soil moisture
        soil_moisture = estimate_soil_moisture(aoi, start_date, end_date)
        soil_moisture_info = soil_moisture.getInfo()
        print(f"Estimated Soil Moisture Info: {soil_moisture_info}")
        
        soil_moisture_url = soil_moisture.getThumbURL({
            'min': -25, 
            'max': 0, 
            'palette': ['blue', 'green', 'yellow', 'red'], 
            'region': aoi.toGeoJSONString(),
            'dimensions': 512
        })

        print(f"Soil Moisture URL: {soil_moisture_url}")

        # Get true color image
        true_color = get_true_color_image(aoi, start_date, end_date)
        true_color_url = true_color.getThumbURL({
            'region': aoi.toGeoJSONString(),
            'dimensions': 512
        })

        print(f"True Color URL: {true_color_url}")

        # Track crop growth and predict yield
        yield_pred, growth_stage = track_crop_growth_and_predict_yield(aoi, start_date, end_date)
        yield_pred_url = yield_pred.getThumbURL({
            'min': 0, 
            'max': 100, 
            'palette': ['blue', 'green', 'yellow', 'red'], 
            'region': aoi.toGeoJSONString(),
            'dimensions': 512
        })

        print(f"Yield Prediction URL: {yield_pred_url}, Growth Stage: {growth_stage}")

        return render_template('results.html', ndvi_url=ndvi_url, evi_url=evi_url, soil_moisture_url=soil_moisture_url, true_color_url=true_color_url, yield_info=yield_pred_url, growth_stage=growth_stage)

    except Exception as e:
        print(f"Error: {str(e)}")
        return str(e), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

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

# Function to estimate soil moisture
def estimate_soil_moisture(aoi, start_date, end_date):
    print(f"Estimating soil moisture for AOI: {aoi.getInfo()}, Date Range: {start_date} to {end_date}")
    
    sentinel1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
                  .filterDate(start_date, end_date) \
                  .filterBounds(aoi) \
                  .filter(ee.Filter.eq('instrumentMode', 'IW')) \
                  .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING')) \
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
                  .select('VV')
    
    soil_moisture = sentinel1.mean().clip(aoi).rename('Soil_Moisture')
    
    return soil_moisture

# Function to get true color image
def get_true_color_image(aoi, start_date, end_date):
    sentinel2 = ee.ImageCollection('COPERNICUS/S2') \
                  .filterDate(start_date, end_date) \
                  .filterBounds(aoi) \
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))

    true_color = sentinel2.median().clip(aoi).visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000)
    return true_color

# Function to track crop growth and predict yield
def track_crop_growth_and_predict_yield(aoi, start_date, end_date):
    ndvi = ee.ImageCollection('COPERNICUS/S2_SR') \
              .filterDate(start_date, end_date) \
              .filterBounds(aoi) \
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
              .map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI')).median().clip(aoi)
    
    yield_prediction = ndvi.multiply(100)
    print(f"Yield prediction: {yield_prediction.getInfo()}")
    
    # Additional Growth Stage Estimation
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
    
    print(f"Mean NDVI: {mean_ndvi}, Growth Stage: {growth_stage}")
    
    return yield_prediction, growth_stage

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
    for rule in app.url_map.iter_rules():
        print(rule)