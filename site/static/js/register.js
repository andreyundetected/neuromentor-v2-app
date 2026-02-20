const form = document.querySelector("form");
const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirm_password");
const errorText = document.getElementById("password-error");

form.addEventListener("submit", function (e) {
    if (password.value !== confirmPassword.value) {
    e.preventDefault();
    confirmPassword.classList.add("error");
    errorText.textContent = "Passwords do not match";
    errorText.style.display = "block";
    } else {
    confirmPassword.classList.remove("error");
    errorText.textContent = "";
    errorText.style.display = "none";
    }
});



const canvas = document.getElementById("backgroundCanvas");
const ctx = canvas.getContext("2d");

let shapes = [];
const shapeCount = 120;

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    createShapes();
}

function createShapes() {
    shapes = [];
    for (let i = 0; i < shapeCount; i++) {
    const size = Math.random() * 30 + 20;
    shapes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: size,
        type: ["triangle0", "triangle1", "triangle2", "triangle3", "square", "circle"][Math.floor(Math.random() * 6)],
        speedX: (Math.random() - 0.5) * 1,
        speedY: (Math.random() - 0.5) * 1
    });
    }
}

function drawShapes() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "rgba(180, 180, 180, 0.5)";
    ctx.lineWidth = 1.5;

    for (let shape of shapes) {
    ctx.beginPath();
    if (shape.type === "triangle0") {
        ctx.moveTo(shape.x, shape.y);
        ctx.lineTo(shape.x + shape.size, shape.y);
        ctx.lineTo(shape.x, shape.y + shape.size);
    } else if (shape.type === "triangle1") {
        ctx.moveTo(shape.x + shape.size, shape.y);
        ctx.lineTo(shape.x, shape.y);
        ctx.lineTo(shape.x + shape.size, shape.y + shape.size);
    } else if (shape.type === "triangle2") {
        ctx.moveTo(shape.x, shape.y + shape.size);
        ctx.lineTo(shape.x, shape.y);
        ctx.lineTo(shape.x + shape.size, shape.y + shape.size);
    } else if (shape.type === "triangle3") {
        ctx.moveTo(shape.x + shape.size, shape.y + shape.size);
        ctx.lineTo(shape.x + shape.size, shape.y);
        ctx.lineTo(shape.x, shape.y + shape.size);
    } else if (shape.type === "square") {
        ctx.rect(shape.x, shape.y, shape.size, shape.size);
    } else if (shape.type === "circle") {
        ctx.arc(shape.x, shape.y, shape.size / 2, 0, Math.PI * 2);
    }
    ctx.closePath();
    ctx.stroke();
    }
}

function updateShapes() {
    for (let shape of shapes) {
    shape.x += shape.speedX;
    shape.y += shape.speedY;

    if (shape.x < 0 || shape.x > canvas.width) shape.speedX *= -1;
    if (shape.y < 0 || shape.y > canvas.height) shape.speedY *= -1;
    }
}

function animate() {
    updateShapes();
    drawShapes();
    requestAnimationFrame(animate);
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
animate();
