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

  // Order Management Modal
  const orderManagementModal = new bootstrap.Modal(
    document.getElementById("orderManagementModal")
  );
  let currentVehicle = null;
  let currentDay = null;

  // Get job_id from a global JS variable or data attribute
  let jobId = window.job_id;
  if (!jobId) {
    // Try to get from a data attribute on a parent element
    const jobIdElem = document.querySelector("[data-job-id]");
    if (jobIdElem) jobId = jobIdElem.getAttribute("data-job-id");
  }

  // Handle manage orders button click
  function renderShopList(shopList) {
    const shopListDiv = document.getElementById("shopListInRoute");
    if (shopList && shopList.length > 0) {
      let table =
        '<table class="table table-bordered table-sm"><thead><tr><th>Shop CODE</th><th>Shop Name</th><th>Action</th></tr></thead><tbody>';
      shopList.forEach((shop) => {
        table += `<tr><td>${shop.CODE}</td><td>${shop.LOCATION}</td><td><button class='btn btn-sm btn-danger remove-shop-btn' data-shop-code='${shop.CODE}'><i class='fas fa-times'></i></button></td></tr>`;
      });
      table += "</tbody></table>";
      shopListDiv.innerHTML = table;
    } else {
      shopListDiv.innerHTML =
        '<div class="alert alert-info">No shops in this route.</div>';
    }
  }

  function renderAvailableOrders(availableOrders) {
    const availableOrdersList = document.getElementById("availableOrders");
    if (availableOrders && availableOrders.length > 0) {
      let select =
        '<div class="input-group mb-2"><select class="form-select" id="availableShopSelect">';
      availableOrders.forEach((order) => {
        select += `<option value="${order.CODE}">${order.CODE} - ${order.LOCATION}</option>`;
      });
      select +=
        '</select><button class="btn btn-success" id="addShopToRouteBtn">Add to Route</button></div>';
      availableOrdersList.innerHTML = select;
    } else {
      availableOrdersList.innerHTML =
        '<div class="alert alert-info">No available shops to add.</div>';
    }
  }

  async function loadRouteOrdersModal() {
    showLoading();
    try {
      const response = await fetch(
        `/api/route-orders?day=${currentDay}&vehicle=${currentVehicle}&job_id=${jobId}`
      );
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Server error:", errorText);
        throw new Error(`Server returned ${response.status}: ${errorText}`);
      }
      const data = await response.json();
      renderShopList(data.shopList);
      renderAvailableOrders(data.availableOrders);
      orderManagementModal.show();
    } catch (error) {
      console.error("Error fetching route orders:", error);
      alert(`Failed to load route orders: ${error.message}`);
    } finally {
      hideLoading();
    }
  }

  document.querySelectorAll(".manage-orders-btn").forEach((button) => {
    button.addEventListener("click", async function (e) {
      e.preventDefault();
      e.stopPropagation();
      const routeLink = this.closest(".route-link");
      currentVehicle = routeLink.dataset.vehicle;
      currentDay = routeLink.dataset.day;
      await loadRouteOrdersModal();
    });
  });

  // Delegate remove button click for shops in route
  $(document).on("click", ".remove-shop-btn", async function () {
    const shopCode = $(this).data("shop-code");
    if (!confirm("Remove this shop from the route?")) return;
    showLoading();
    try {
      const response = await fetch("/api/remove-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          orderId: shopCode,
          day: currentDay,
          vehicle: currentVehicle,
          job_id: jobId,
        }),
      });
      const data = await response.json();
      if (data.success) {
        await loadRouteOrdersModal();
      } else {
        alert("Failed to remove shop: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      alert("Error removing shop: " + error.message);
    } finally {
      hideLoading();
    }
  });

  // Delegate add button click for available shop
  $(document).on("click", "#addShopToRouteBtn", async function () {
    const select = document.getElementById("availableShopSelect");
    const shopCode = select.value;
    if (!shopCode) return;
    showLoading();
    try {
      const response = await fetch("/api/add-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          orderId: shopCode,
          day: currentDay,
          vehicle: currentVehicle,
          job_id: jobId,
        }),
      });
      const data = await response.json();
      if (data.success) {
        await loadRouteOrdersModal();
      } else {
        alert("Failed to add shop: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      alert("Error adding shop: " + error.message);
    } finally {
      hideLoading();
    }
  });

  // Handle order search
  const orderSearchInput = document.getElementById("orderSearchInput");
  const orderSearchBtn = document.getElementById("orderSearchBtn");

  function filterOrders() {
    const searchTerm = orderSearchInput.value.toLowerCase();
    const availableOrders = document.querySelectorAll(
      "#availableOrders .list-group-item"
    );

    availableOrders.forEach((order) => {
      const orderText = order.textContent.toLowerCase();
      order.style.display = orderText.includes(searchTerm) ? "" : "none";
    });
  }

  orderSearchInput.addEventListener("input", filterOrders);
  orderSearchBtn.addEventListener("click", filterOrders);

  // Handle add/remove order buttons
  document.addEventListener("click", async function (e) {
    if (e.target.closest(".add-order-btn")) {
      const orderItem = e.target.closest(".list-group-item");
      const orderId = orderItem.dataset.orderId;

      try {
        const response = await fetch("/api/add-order", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            orderId,
            day: currentDay,
            vehicle: currentVehicle,
          }),
        });

        if (response.ok) {
          // Move order to current orders list
          orderItem.querySelector(".add-order-btn").className =
            "btn btn-sm btn-danger remove-order-btn";
          orderItem.querySelector(".remove-order-btn i").className =
            "fas fa-times";
          document.getElementById("currentOrders").appendChild(orderItem);
        } else {
          throw new Error("Failed to add order");
        }
      } catch (error) {
        console.error("Error adding order:", error);
        alert("Failed to add order. Please try again.");
      }
    }

    if (e.target.closest(".remove-order-btn")) {
      const orderId = e.target
        .closest(".remove-order-btn")
        .getAttribute("data-order-id");

      try {
        const response = await fetch("/api/remove-order", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            orderId,
            day: currentDay,
            vehicle: currentVehicle,
          }),
        });

        if (response.ok) {
          // Move order to available orders list
          const orderItem = document
            .querySelector(`.remove-order-btn[data-order-id="${orderId}"]`)
            .closest(".list-group-item");
          orderItem.querySelector(".remove-order-btn").className =
            "btn btn-sm btn-success add-order-btn";
          orderItem.querySelector(".add-order-btn i").className = "fas fa-plus";
          document.getElementById("availableOrders").appendChild(orderItem);
        } else {
          throw new Error("Failed to remove order");
        }
      } catch (error) {
        console.error("Error removing order:", error);
        alert("Failed to remove order. Please try again.");
      }
    }
  });

  // Handle save changes
  document
    .getElementById("saveOrderChanges")
    .addEventListener("click", async function () {
      try {
        showLoading();

        const currentOrders = Array.from(
          document.querySelectorAll("#currentOrders .list-group-item")
        ).map((item) => item.dataset.orderId);

        const response = await fetch("/api/save-route-orders", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            day: currentDay,
            vehicle: currentVehicle,
            orders: currentOrders,
          }),
        });

        if (response.ok) {
          orderManagementModal.hide();
          // Refresh the route display
          const routeLink = document.querySelector(
            `.route-link[data-day="${currentDay}"][data-vehicle="${currentVehicle}"]`
          );
          if (routeLink) {
            routeLink.click();
          }
        } else {
          throw new Error("Failed to save changes");
        }
      } catch (error) {
        console.error("Error saving changes:", error);
        alert("Failed to save changes. Please try again.");
      } finally {
        hideLoading();
      }
    });

  // Handle open map in new window
  document.querySelectorAll(".open-map-btn").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      const routeLink = this.closest(".route-link");
      const mapUrl = routeLink.dataset.file;
      window.open(mapUrl, "_blank");
    });
  });

  // Handle add by CODE
  document
    .getElementById("addOrderByCodeBtn")
    .addEventListener("click", async function () {
      const codeInput = document.getElementById("addOrderCodeInput");
      const orderId = codeInput.value.trim();
      if (!orderId) return;
      showLoading();
      try {
        const response = await fetch("/api/add-order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            orderId,
            day: currentDay,
            vehicle: currentVehicle,
          }),
        });
        const result = await response.json();
        if (response.ok && result.success) {
          // Refresh the order lists
          const ordersResp = await fetch(
            `/api/route-orders?day=${currentDay}&vehicle=${currentVehicle}`
          );
          const data = await ordersResp.json();
          // Repopulate current orders
          const currentOrdersList = document.getElementById("currentOrders");
          currentOrdersList.innerHTML = data.currentOrders
            .map(
              (order) => `
          <div class=\"list-group-item d-flex justify-content-between align-items-center\" data-order-id=\"${order.id}\">\n            <div>\n              <strong>${order.id}</strong><br>\n              <small>${order.location}</small>\n            </div>\n            <button class=\"btn btn-sm btn-danger remove-order-btn\">\n              <i class=\"fas fa-times\"></i>\n            </button>\n          </div>\n        `
            )
            .join("");
          // Optionally, also refresh available orders
          const availableOrdersList =
            document.getElementById("availableOrders");
          availableOrdersList.innerHTML = data.availableOrders
            .map(
              (order) => `
          <div class=\"list-group-item d-flex justify-content-between align-items-center\" data-order-id=\"${order.id}\">\n            <div>\n              <strong>${order.id}</strong><br>\n              <small>${order.location}</small>\n            </div>\n            <button class=\"btn btn-sm btn-success add-order-btn\">\n              <i class=\"fas fa-plus\"></i>\n            </button>\n          </div>\n        `
            )
            .join("");
          codeInput.value = "";
        } else {
          alert(result.error || "Order not found or already assigned.");
        }
      } catch (error) {
        alert("Failed to add order by CODE.");
      } finally {
        hideLoading();
      }
    });

  // Submit All Routes button logic
  const submitBtn = document.getElementById("submitRoutesBtn");
  if (submitBtn) {
    submitBtn.addEventListener("click", async function () {
      showLoading();
      try {
        // Fetch job info
        const response = await fetch(`/api/job/${jobId}`);
        if (!response.ok) throw new Error("Failed to fetch job info");
        const jobInfo = await response.json();
        const numVehicles = jobInfo.num_vehicles;
        const day = 1; // Adjust if you support multi-day
        let routes = [];
        for (let v = 0; v < numVehicles; v++) {
          const routeRes = await fetch(
            `/api/route-orders?day=${day}&vehicle=${v}&job_id=${jobId}`
          );
          if (!routeRes.ok) continue;
          const data = await routeRes.json();
          routes.push({
            vehicle: v,
            shopList: data.shopList,
          });
        }
        // Send to external API (replace URL below)
        const externalApiUrl = "https://your-external-api.com/submit";
        const submitRes = await fetch(externalApiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(routes),
        });
        if (!submitRes.ok) throw new Error("Failed to submit to external API");
        showToast("Routes submitted successfully!", true);
      } catch (err) {
        showToast("Error submitting routes: " + err.message, false);
      } finally {
        hideLoading();
      }
    });
  }
});

function showToast(message, isSuccess = true) {
  // If Bootstrap toast container exists, use it
  let toastContainer = document.querySelector(".toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.className =
      "toast-container position-fixed bottom-0 end-0 p-3";
    document.body.appendChild(toastContainer);
  }
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-white bg-${
    isSuccess ? "success" : "danger"
  }`;
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();
}
