// 主页面填充教室列表（动态容量）
if (document.body.classList.contains("main-page")) {
  const cameraToRoom = {
    "camera_0": { name: "101", noise: "安静" },
    "camera_1": { name: "102", noise: "嘈杂" },
    "camera_2": { name: "203", noise: "嘈杂" }
  };

  fetch("/api/summary")
    .then(res => res.json())
    .then(data => {
      for (const [cameraId, status] of Object.entries(data)) {
        const { name, noise } = cameraToRoom[cameraId];
        const span = document.getElementById(`room-${name}-detail`);
        if (span) {
          span.textContent = `容量: ${status.occupied}/${status.total} | ${noise}`;
        }
      }
    });
}

// 详情页加载
if (document.body.classList.contains("room-page")) {
  const url = new URL(location.href);
  const room = url.searchParams.get("room");
  document.getElementById("room-name").textContent = room;

  // 示例生成 15 个座位
  const seatGrid = document.getElementById("seat-grid");
  for (let i = 0; i < 15; i++) {
    const div = document.createElement("div");
    div.className = ["green", "red", "orange"][i % 3];
    div.textContent = `Seat ${i + 1}`;
    seatGrid.appendChild(div);
  }

  // 模拟分贝
  document.getElementById("noise-status").textContent =
    `当前分贝：${Math.floor(Math.random() * 20 + 40)} dB 🎵`;
}
