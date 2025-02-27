// main/app/static/js/waves.js
function initWaves() {
    const canvas = document.getElementById('waveCanvas');
    if (!canvas) return;

    // Konfigurační objekt pro vlny (dostupný globálně)
    window.wavesConfig = window.wavesConfig || {
        speedMultiplier: 0.5 // Výchozí hodnota rychlosti
    };

    const ctx = canvas.getContext('2d');
    const waveHeights = [30, 25, 20];
    const waveSpeeds = [Math.random() * 0.1 + 0.2, Math.random() * 0.2 + 0.2, Math.random() * 0.25 + 0.2];
    let offset = [0, 0, 0];
    let verticalOffsets = [0, 0, 0];
    let lastTime = performance.now();

    const randomFactors = waveHeights.map(() => ({
        speed: Math.random() * 0.5 + 0.2,
        verticalMovement: Math.random() * 30 + 5,
        offsetFactor: Math.random() * 4 + 1,
    }));

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function drawWaves(timestamp) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        let deltaTime = (timestamp - lastTime) / 1000;
        lastTime = timestamp;

        // Pozadí s gradientem
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#E31837');
        gradient.addColorStop(1, '#0070BB');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < waveHeights.length; i++) {
            const speedFactor = waveSpeeds[i] * deltaTime * 100 * randomFactors[i].offsetFactor * window.wavesConfig.speedMultiplier;
            
            if (i === 1) {
                offset[i] -= speedFactor;
            } else {
                offset[i] += speedFactor;
            }

            verticalOffsets[i] = Math.sin(timestamp * 0.001 * randomFactors[i].speed + i) * randomFactors[i].verticalMovement;
            drawWave(i);
        }

        requestAnimationFrame(drawWaves);
    }

    function drawWave(index) {
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, `rgba(255, 255, 255, ${(index + 1) * 0.2})`);
        gradient.addColorStop(1, `rgba(230, 230, 230, ${(index + 1) * 0.4})`);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(0, canvas.height * 0.3 + verticalOffsets[index]);

        const amplitude = waveHeights[index];
        const frequency = 0.02;

        for (let x = 0; x <= canvas.width; x++) {
            const y = canvas.height * 0.8 + amplitude * Math.sin(frequency * (x + offset[index])) + verticalOffsets[index];
            ctx.lineTo(x, y);
        }

        ctx.lineTo(canvas.width, canvas.height);
        ctx.lineTo(0, canvas.height);
        ctx.closePath();
        ctx.fill();
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    requestAnimationFrame(drawWaves);
}

document.addEventListener('DOMContentLoaded', initWaves);