// 主页面填充教室列表
if (document.body.classList.contains("main-page")) {
  const rooms = [
    { name: "101", people: "3/45", noise: "安静" },
    { name: "102", people: "1/40", noise: "嘈杂" },
    { name: "203", people: "38/40", noise: "嘈杂" }
  ];

  const tbody = document.getElementById("room-list");
  rooms.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><a href="room.html?room=${r.name}">${r.name}</a></td>
                    <td>${r.people}</td><td>${r.noise}</td>`;
    tbody.appendChild(tr);
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
    div.className = ["green","red","orange"][i % 3];
    div.textContent = `Seat ${i+1}`;
    seatGrid.appendChild(div);
  }

  // 模拟分贝
  document.getElementById("noise-status").textContent = `当前分贝：${Math.floor(Math.random()*20+40)} dB 🎵`;
}

