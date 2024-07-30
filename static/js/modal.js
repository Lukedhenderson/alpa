// Get the modal elements
var modal = document.getElementById("image-modal");
var modalImg = document.getElementById("enlarged-image");
var captionText = document.getElementById("caption");

// Open modal when an image is clicked
function openModal(event) {
    modal.style.display = "block";
    modalImg.src = event.target.src; // Set the src of the modal image to the clicked image's src
    captionText.innerHTML = event.target.alt; // Set the caption to the alt text
}

// Close the modal when clicking on the close button
var span = document.getElementsByClassName("close")[0];
span.onclick = function() {
    modal.style.display = "none";
}

// Close the modal when clicking outside the image
modal.onclick = function(event) {
    if (event.target === modal) {
        modal.style.display = "none";
    }
}

// Add event listeners to all clickable images
var images = document.getElementsByClassName("clickable-image");
for (var i = 0; i < images.length; i++) {
    images[i].onclick = openModal;
}