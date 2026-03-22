// YeyoOS — Double Grid Background Fragment Shader
// Micro-fase 3.18 — Capa 3: Cuerpo
//
// Doble cuadrícula: líneas finas cada 20px + líneas gruesas cada 100px
// u_saturation: 0.0 = gris completo, 1.0 = azul completo
// u_time: tiempo en segundos para animaciones futuras
// u_color: color base de la cuadrícula (vec3 RGB 0.0-1.0)
// u_resolution: resolución del canvas en píxeles

precision mediump float;

uniform float u_time;
uniform vec3 u_color;
uniform float u_saturation;
uniform vec2 u_resolution;

void main() {
  vec2 uv = gl_FragCoord.xy;

  // Fondo base: #050A14 (casi negro, tinte azul marino)
  vec3 bgColor = vec3(0.020, 0.039, 0.078);

  // --- Capa 1: líneas finas cada 20px, grosor 0.5px ---
  float gridSmall = 20.0;
  vec2 modSmall = mod(uv, gridSmall);
  float lineSmall = step(modSmall.x, 0.5) + step(modSmall.y, 0.5);
  lineSmall = clamp(lineSmall, 0.0, 1.0);
  float alphaSmall = 0.10;

  // --- Capa 2: líneas gruesas cada 100px, grosor 1px ---
  float gridLarge = 100.0;
  vec2 modLarge = mod(uv, gridLarge);
  float lineLarge = step(modLarge.x, 1.0) + step(modLarge.y, 1.0);
  lineLarge = clamp(lineLarge, 0.0, 1.0);
  float alphaLarge = 0.22;

  // Color base de la cuadrícula: #4FC3F7 = vec3(0.310, 0.765, 0.969)
  vec3 gridColorBase = vec3(0.310, 0.765, 0.969);

  // Mezclar color usuario con color base
  vec3 gridColor = mix(gridColorBase, u_color, 0.5);

  // Aplicar saturación: mezcla entre gris y color
  float luma = dot(gridColor, vec3(0.299, 0.587, 0.114));
  vec3 gridColorSat = mix(vec3(luma), gridColor, u_saturation);

  // Combinar capas
  vec3 finalColor = bgColor;
  finalColor = mix(finalColor, gridColorSat, lineSmall * alphaSmall);
  finalColor = mix(finalColor, gridColorSat, lineLarge * alphaLarge);

  gl_FragColor = vec4(finalColor, 1.0);
}
