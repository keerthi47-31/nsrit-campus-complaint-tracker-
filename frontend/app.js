const $ = (selector) => document.querySelector(selector);

const studentView = $("#studentView");
const loginView = $("#loginView");
const adminView = $("#adminView");

function showView(view) {
  studentView.classList.add("hidden");
  loginView.classList.add("hidden");
  adminView.classList.add("hidden");

  view.classList.remove("hidden");
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}

function statusClass(status) {
  if (status === "Open") return "open";
  if (status === "In Progress") return "progress";
  return "resolved";
}

function complaintCard(item, isAdmin = false) {
  let adminControls = "";

  if (isAdmin) {
    adminControls = `
      <div class="admin-actions">
        <select id="status-${item.id}">
          <option ${item.status === "Open" ? "selected" : ""}>Open</option>
          <option ${item.status === "In Progress" ? "selected" : ""}>In Progress</option>
          <option ${item.status === "Resolved" ? "selected" : ""}>Resolved</option>
        </select>

        <button data-update="${item.id}">Update Status</button>
      </div>
    `;
  }

  let studentDetails = "";

  if (isAdmin) {
    studentDetails = `
      <span>
        <b>Student:</b> ${item.student_name}
        (${item.student_department})
      </span>
    `;
  }

  return `
    <article class="complaint">
      <h3>#${item.id} — ${item.title}</h3>

      <p>${item.description}</p>

      <div class="details">
        ${studentDetails}
        <span><b>Category:</b> ${item.category}</span>
        <span><b>Location:</b> ${item.location}</span>
        <span class="priority-${item.priority.toLowerCase()}">
          <b>Priority:</b> ${item.priority}
        </span>
        <span><b>Created:</b> ${item.created_at}</span>
      </div>

      <p>
        <span class="tag ${statusClass(item.status)}">
          ${item.status}
        </span>
      </p>

      ${adminControls}
    </article>
  `;
}

async function loadComplaints(isAdmin = false) {
  let url = "/api/complaints";

  if (isAdmin) {
    const status = $("#statusFilter").value;
    url += `?status=${encodeURIComponent(status)}`;
  }

  const complaints = await api(url);

  const list = isAdmin ? $("#adminList") : $("#studentList");

  if (complaints.length === 0) {
    list.innerHTML = "<p>No complaints found.</p>";
  } else {
    list.innerHTML = complaints
      .map((item) => complaintCard(item, isAdmin))
      .join("");
  }

  if (isAdmin) {
    const openCount = complaints.filter((item) => item.status === "Open").length;
    const progressCount = complaints.filter(
      (item) => item.status === "In Progress"
    ).length;
    const resolvedCount = complaints.filter(
      (item) => item.status === "Resolved"
    ).length;

    $("#stats").innerHTML = `
      <div class="stat"><b>${openCount}</b>Open</div>
      <div class="stat"><b>${progressCount}</b>In Progress</div>
      <div class="stat"><b>${resolvedCount}</b>Resolved</div>
    `;

    document.querySelectorAll("[data-update]").forEach((button) => {
      button.addEventListener("click", async () => {
        const id = button.dataset.update;
        const newStatus = $(`#status-${id}`).value;

        try {
          await api(`/api/complaints/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ status: newStatus })
          });

          await loadComplaints(true);
        } catch (error) {
          alert(error.message);
        }
      });
    });
  }
}

$("#complaintForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const complaint = {
    student_name: $("#student_name").value,
    student_department: $("#student_department").value,
    title: $("#title").value,
    category: $("#category").value,
    location: $("#location").value,
    priority: $("#priority").value,
    description: $("#description").value
  };

  const message = $("#formMessage");

  try {
    await api("/api/complaints", {
      method: "POST",
      body: JSON.stringify(complaint)
    });

    event.target.reset();

    message.textContent =
      "Complaint submitted successfully. Your status is Open.";

    message.classList.remove("error");

    await loadComplaints();
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
});

$("#adminButton").addEventListener("click", async () => {
  const user = await api("/api/auth/me");

  if (user.is_admin) {
    showView(adminView);
    await loadComplaints(true);
  } else {
    showView(loginView);
  }
});

$("#backButton").addEventListener("click", () => {
  showView(studentView);
});

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = $("#loginMessage");

  try {
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#username").value,
        password: $("#password").value
      })
    });

    event.target.reset();

    showView(adminView);
    await loadComplaints(true);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
});

$("#logoutButton").addEventListener("click", async () => {
  await api("/api/auth/logout", {
    method: "POST"
  });

  showView(studentView);
});

$("#statusFilter").addEventListener("change", () => {
  loadComplaints(true);
});

loadComplaints();
