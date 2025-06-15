let generatedParticles = [];
let controller = new AbortController();

function setup() {
    let canvas = createCanvas(600, 450);
    canvas.parent('canvas-container');
    background(200);
}

function draw() {
    background(200); // 灰色背景

    // 白底圆角容器
    fill(255);
    noStroke();
    rect(50, 50, 500, 300, 20);

    // 绘制粒子图（位于容器内）
    push();
    translate(50, 50); // 粒子偏移到容器区域
    for (let p of generatedParticles) {
        p.update();
        p.show();
    }
    pop();

    // 图例说明
    fill(0);
    textSize(14);
    text("座位图说明：", 50, 370);

    fill("red");
    rect(140, 358, 12, 12, 3);
    fill(0);
    text("占用", 160, 370);

    fill("green");
    rect(210, 358, 12, 12, 3);
    fill(0);
    text("空闲", 230, 370);

    text("功能：输入提示词生成座位图粒子动画", 50, 395);
}

class Particle {
    constructor(x, y, col) {
        this.home = createVector(x, y);
        this.pos = createVector(x, y);
        this.col = col;
    }

    update() {
        let mouse = createVector(mouseX, mouseY);
        let d = dist(this.pos.x, this.pos.y, mouse.x, mouse.y);
        if (d < 80) {
            let diff = p5.Vector.sub(this.pos, mouse);
            diff.setMag(5);
            this.pos.add(diff);
        } else {
            this.pos.lerp(this.home, 0.05);
        }
    }

    show() {
        noStroke();
        fill(this.col);
        circle(this.pos.x, this.pos.y, 4);
    }
}

async function onGenerateClick() {
    const prompt = document.getElementById("prompt").value;
    if (!prompt) {
        alert("请输入提示词！");
        return;
    }

    const loadingElement = document.getElementById("loading");
    const cancelBtn = document.getElementById("cancel-btn");

    loadingElement.style.display = "block";
    cancelBtn.style.display = "inline";

    try {
        const blob = await generateImage(prompt);
        const imgURL = URL.createObjectURL(blob);

        loadImage(imgURL, loaded => {
            loaded.resize(500, 300); // 尺寸与容器一致
            loaded.loadPixels();

            generatedParticles = [];
            for (let x = 0; x < loaded.width; x += 8) {
                for (let y = 0; y < loaded.height; y += 8) {
                    let i = (y * loaded.width + x) * 4;
                    let r = loaded.pixels[i];
                    let g = loaded.pixels[i + 1];
                    let b = loaded.pixels[i + 2];
                    generatedParticles.push(new Particle(x, y, color(r, g, b)));
                }
            }
        });
    } catch (err) {
        alert("生成失败：" + err.message);
    } finally {
        loadingElement.style.display = "none";
        cancelBtn.style.display = "none";
    }
}

async function generateImage(prompt) {
    const response = await fetch("/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt }),
        signal: controller.signal
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API 错误: ${errorText}`);
    }

    return await response.blob();
}

function cancelRequest() {
    controller.abort();
    controller = new AbortController();
}
