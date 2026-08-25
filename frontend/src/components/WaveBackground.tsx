import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useTheme } from '../theme/ThemeContext'

// Domain-warped simplex fBm drives vertex displacement (Inigo Quilez-style
// two-stage warp: fbm(p + k*n(p + k*n(p)))), giving a slow, asymmetric,
// non-repeating swirl instead of crossing sine ripples. A finite-difference
// normal (no closed-form derivative exists for this noise field) drives a
// crest-masked fresnel rim in the fragment shader. See workflow synthesis
// rationale for the full perf/legibility breakdown.
const VERTEX_SHADER = `
uniform float uTime;

varying float vElevation;
varying float vWarp;
varying vec3 vNormal;
varying vec3 vViewPosition;

// Simplex noise (3D), Ashima Arts / Stefan Gustavson, MIT licensed
// (https://github.com/ashima/webgl-noise). Inlined: no external textures.
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

// 3-octave fbm, fixed small iteration count so it unrolls cleanly.
float fbm(vec3 p) {
  float sum = 0.0;
  float amp = 0.5;
  float freq = 1.0;
  for (int i = 0; i < 3; i++) {
    sum += amp * snoise(p * freq);
    freq *= 2.0;
    amp *= 0.5;
  }
  return sum;
}

// Domain-warped fBm height field. Returns elevation in ~[-0.9, 0.9] and
// writes a secondary "warp strength" used for a fragment-side tonal bias.
float getElevation(vec2 p, float t, out float warpOut) {
  vec2 base = p * 0.16;

  float tSlow = t * 0.045;
  float tWarp = t * 0.07;

  vec2 q = vec2(
    snoise(vec3(base, tSlow)),
    snoise(vec3(base + vec2(5.2, 1.3), tSlow))
  );

  vec2 r = vec2(
    snoise(vec3(base + 1.6 * q + vec2(1.7, 9.2), tWarp + 2.0)),
    snoise(vec3(base + 1.6 * q + vec2(8.3, 2.8), tWarp + 4.0))
  );

  float n = fbm(vec3(base + 2.2 * r, tSlow * 0.6));

  warpOut = clamp(length(r) * 0.6, 0.0, 1.0);
  return n;
}

void main() {
  vec3 pos = position;

  float warp;
  float n = getElevation(pos.xy, uTime, warp);
  float elevation = n * 0.55;
  pos.z += elevation;

  // Finite-difference normal (this noise field has no closed-form
  // derivative), 2 extra height samples per vertex, not per fragment.
  float eps = 0.4;
  float warpUnused;
  float nX = getElevation(pos.xy + vec2(eps, 0.0), uTime, warpUnused);
  float nY = getElevation(pos.xy + vec2(0.0, eps), uTime, warpUnused);

  float dHdx = (nX * 0.55 - elevation) / eps;
  float dHdy = (nY * 0.55 - elevation) / eps;

  vec3 localNormal = normalize(vec3(-dHdx, -dHdy, 1.0));

  vElevation = n;
  vWarp = warp;
  vNormal = normalize(normalMatrix * localNormal);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  vViewPosition = -mvPosition.xyz;

  gl_Position = projectionMatrix * mvPosition;
}
`

const FRAGMENT_SHADER = `
uniform vec3 uColorLow;
uniform vec3 uColorHigh;
uniform float uOpacity;

varying float vElevation;
varying float vWarp;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  vec3 normal  = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);

  float mixFactor = smoothstep(-0.55, 0.55, vElevation);
  vec3 color = mix(uColorLow, uColorHigh, mixFactor);

  // Fresnel rim from the finite-difference normal: grazing angles glow,
  // masked to wave crests so troughs stay calm behind foreground cards.
  float NdotV = clamp(dot(normal, viewDir), 0.0, 1.0);
  float fresnel = pow(1.0 - NdotV, 3.0);
  float crestMask = smoothstep(0.35, 0.75, vElevation);
  float rim = fresnel * crestMask;

  vec3 rimColor = mix(uColorHigh, vec3(1.0), 0.2);
  color += rimColor * rim * 0.18;
  color = clamp(color, 0.0, 1.0);

  color = mix(color, mix(uColorLow, uColorHigh, 0.5), vWarp * 0.1);

  float alpha = clamp(uOpacity * (1.0 + rim * 0.25), 0.0, 1.0);

  gl_FragColor = vec4(color, alpha);
}
`

const DARK_COLORS = { low: '#0b1220', high: '#22d3ee', opacity: 0.45 }
const LIGHT_COLORS = { low: '#dbeafe', high: '#a78bfa', opacity: 0.3 }

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function DprCap() {
  const { gl } = useThree()
  useEffect(() => {
    gl.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
  }, [gl])
  return null
}

function WavePlane({ colorLow, colorHigh, opacity }: { colorLow: string; colorHigh: string; opacity: number }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null)
  const reduced = useMemo(prefersReducedMotion, [])

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColorLow: { value: new THREE.Color(colorLow) },
      uColorHigh: { value: new THREE.Color(colorHigh) },
      uOpacity: { value: opacity },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useEffect(() => {
    uniforms.uColorLow.value.set(colorLow)
    uniforms.uColorHigh.value.set(colorHigh)
    uniforms.uOpacity.value = opacity
  }, [colorLow, colorHigh, opacity, uniforms])

  useFrame((_, delta) => {
    if (reduced || !materialRef.current) return
    materialRef.current.uniforms.uTime.value += delta
  })

  return (
    <mesh rotation={[-Math.PI / 2.4, 0, 0]} position={[0, -1.4, 0]}>
      <planeGeometry args={[16, 16, 96, 96]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={VERTEX_SHADER}
        fragmentShader={FRAGMENT_SHADER}
        uniforms={uniforms}
        transparent
      />
    </mesh>
  )
}

export default function WaveBackground() {
  const { theme } = useTheme()
  const colors = theme === 'dark' ? DARK_COLORS : LIGHT_COLORS

  return (
    <div className="fixed inset-0 -z-10 pointer-events-none">
      <Canvas camera={{ position: [0, 1.6, 5], fov: 55 }} gl={{ antialias: true, alpha: true }}>
        <DprCap />
        <WavePlane colorLow={colors.low} colorHigh={colors.high} opacity={colors.opacity} />
      </Canvas>
      <div className="absolute inset-0 bg-gradient-to-b from-white/50 via-transparent to-white/70 dark:from-black/40 dark:via-transparent dark:to-black/70" />
    </div>
  )
}
