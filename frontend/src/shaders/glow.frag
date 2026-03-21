precision mediump float;

varying vec2 vTextureCoord;
uniform sampler2D uTexture;
uniform float uTime;
uniform float uPulseSpeed;
uniform vec3 uGlowColor;
uniform float uGlowIntensity;
uniform float uRadius;

void main() {
    vec2 uv = vTextureCoord;
    vec2 center = vec2(0.5, 0.5);
    float dist = distance(uv, center);

    float pulse = sin(uTime * uPulseSpeed) * 0.5 + 0.5;
    float glowRadius = uRadius * (1.0 + pulse * 0.3);

    float glow = smoothstep(glowRadius, glowRadius * 0.3, dist);
    glow *= uGlowIntensity * (0.7 + pulse * 0.3);

    vec4 texColor = texture2D(uTexture, uv);
    vec3 finalColor = mix(texColor.rgb, uGlowColor, glow * 0.6);
    float finalAlpha = max(texColor.a, glow * 0.8);

    gl_FragColor = vec4(finalColor, finalAlpha);
}
