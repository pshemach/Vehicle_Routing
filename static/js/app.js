// Common JavaScript functions for the Vehicle Routing Solution

// Show loading overlay
function showLoading() {
  const overlay = document.createElement("div");
  overlay.className = "loading-overlay";
  overlay.innerHTML = `
        <div class="spinner-border text-light loading-spinner" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
  document.body.appendChild(overlay);
}

// Hide loading overlay
function hideLoading() {
  const overlay = document.querySelector(".loading-overlay");
  if (overlay) {
    overlay.remove();
  }
}

// Format date
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

// Format file size
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Generate a random color
function getRandomColor() {
  const letters = "0123456789ABCDEF";
  let color = "#";
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

// Copy text to clipboard
function copyToClipboard(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);

  // Show toast notification
  const toast = document.createElement("div");
  toast.className = "toast align-items-center text-white bg-success";
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");
  toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                Copied to clipboard!
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

  const toastContainer = document.querySelector(".toast-container");
  if (!toastContainer) {
    const container = document.createElement("div");
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    document.body.appendChild(container);
    container.appendChild(toast);
  } else {
    toastContainer.appendChild(toast);
  }

  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();
}

function generateVehicleFields() {
  const numVehicles = parseInt($("#num_vehicles").val());
  let html = "";

  for (let i = 0; i < numVehicles; i++) {
    // Try to get previous values if the fields already exist
    const existingVisits = $(`#max_visits_${i}`).val() || 15;
    const existingDistance = $(`#max_distance_${i}`).val() || 100;

    html += `
        <div class="vehicle-config card mb-2">
          <div class="card-header bg-light">
            <h6 class="mb-0">Vehicle ${i + 1}</h6>
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-md-6">
                <label for="max_visits_${i}" class="form-label">Max Visits</label>
                <input type="number" class="form-control" id="max_visits_${i}" name="max_visits[${i}]" value="${existingVisits}" min="1">
                <div class="form-text">Maximum number of visits for this vehicle.</div>
              </div>
              <div class="col-md-6">
                <label for="max_distance_${i}" class="form-label">Max Distance (km)</label>
                <input type="number" class="form-control" id="max_distance_${i}" name="max_distance[${i}]" value="${existingDistance}" min="1">
                <div class="form-text">Maximum distance for this vehicle in kilometers.</div>
              </div>
            </div>
          </div>
        </div>
      `;
  }

  $("#vehicle-config-container").html(html);
}

// Document ready function
document.addEventListener("DOMContentLoaded", function () {
  // Add custom event listeners here

  // Example: Add copy button functionality
  document.querySelectorAll(".copy-btn").forEach((button) => {
    button.addEventListener("click", function () {
      const text = this.getAttribute("data-copy");
      copyToClipboard(text);
    });
  });
});
