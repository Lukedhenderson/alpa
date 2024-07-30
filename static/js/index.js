mapboxgl.accessToken = 'pk.eyJ1IjoibHVrZWRoZW5kZXJzb24iLCJhIjoiY2x6NHU0a3VxMGFvNDJucTBub3ltanNkZiJ9.Z-2cOmjMEKBwXj93okycCg';

const map = new mapboxgl.Map({
    container: 'map', // container ID
    style: 'mapbox://styles/mapbox/satellite-v9', // style URL
    center: [-91.874, 42.76], // starting position [lng, lat]
    zoom: 12 // starting zoom
});

const draw = new MapboxDraw({
    displayControlsDefault: false,
    controls: {
        polygon: true,
        trash: true // Enable delete control
    }
});

map.addControl(draw, 'top-right');

const geolocate = new mapboxgl.GeolocateControl({
    positionOptions: {
        enableHighAccuracy: true
    },
    trackUserLocation: true,
    showUserLocation: true
});

map.addControl(geolocate, 'bottom-right');

map.on('draw.create', updateAOI);
map.on('draw.update', updateAOI);
map.on('draw.delete', clearAOI);

function updateAOI(e) {
    const data = draw.getAll();
    if (data.features.length > 0) {
        const aoi = data.features[0].geometry;
        document.getElementById('aoi').value = JSON.stringify(aoi);
        console.log("AOI: ", aoi);
    }
}

function clearAOI() {
    document.getElementById('aoi').value = '';
}