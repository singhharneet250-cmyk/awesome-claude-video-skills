/*
 * White Glass 3D: a physically based studio for realistic, deterministic renders.
 *
 * Every frame is a pure function of time, so scripts/render.cjs can seek any frame.
 *   - materials: white ceramic, frosted glass, one signal-orange accent (PBR, clearcoat, sheen)
 *   - light: studio environment map for real reflections, a soft key light, a shadow-catcher floor
 *     (the floor draws only the shadow, so it also works over footage in transparent mode)
 *   - camera: lens shift (verticals stay straight); with camera.samples > 1, each frame averages
 *     sub-frames spread over the shutter (motion blur, 180° by default) and over the lens aperture
 *     (depth of field), the way a real camera exposes a frame
 *   - the 3D layer renders with a transparent background over the HTML stage, so the brand
 *     background (white → ice gradient and soft discs) is exact and footage overlays keep their alpha
 *   - tone mapping: Khronos PBR Neutral, so the brand whites stay white
 *
 * Used by templates/molecule-3d.html and templates/product-hero-3d.html. Brand rules: SKILL.md §2, §4, §5.
 */
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

export { THREE };

export const COLORS = { porcelain: "#FFFFFF", ice: "#EAF0F6", ink: "#202B38", orange: "#F0782B", slate: "#596879" };

/* ---------- time ---------- */

/** cubic-bezier(x1, y1, x2, y2) as a function of progress 0..1 (same curves as brand.css). */
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const x = (u) => ((ax * u + bx) * u + cx) * u;
  const y = (u) => ((ay * u + by) * u + cy) * u;
  const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
  return (p) => {
    if (p <= 0) return 0;
    if (p >= 1) return 1;
    let u = p;
    for (let i = 0; i < 8; i++) {
      const e = x(u) - p, d = dx(u);
      if (Math.abs(e) < 1e-6 || Math.abs(d) < 1e-6) break;
      u -= e / d;
    }
    return y(Math.min(1, Math.max(0, u)));
  };
}
export const ease = {
  out: bezier(0.22, 1, 0.36, 1),      // glass reveal, kinetic type
  float: bezier(0.37, 0, 0.63, 1),    // 3D float, camera drift
  in: bezier(0.64, 0, 0.78, 0),       // exits
};
export const clamp01 = (x) => Math.min(1, Math.max(0, x));
/** progress of t through [start, start + dur], eased */
export const span = (t, start, dur, fn = ease.out) => fn(clamp01((t - start) / dur));
/** brand float: ±1 sine wave with the given period (seconds) */
export const floatWave = (t, period = 2.6) => {
  const half = period / 2, k = Math.floor(t / half), p = (t - k * half) / half;
  const v = ease.float(p) * 2 - 1;
  return k % 2 === 0 ? v : -v;
};

/* ---------- materials ---------- */

export const materials = {
  ceramic: (color = "#F4F6F9") => new THREE.MeshPhysicalMaterial({
    color, roughness: 0.3, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.12,
  }),
  // Frosted glass without refraction: an ice-tinted, semi-opaque body with a sharp clearcoat and a soft
  // white rim. (Real transmission breaks over a transparent background in software GL, and the HTML
  // stage needs that background, so this is the reliable look; bonds show faintly through, as in glass.)
  // Over footage (overFootage) the glass goes near-opaque, like the brand's glass panels do.
  frosted: (overFootage = false) => new THREE.MeshPhysicalMaterial({
    color: "#E8EFF6", roughness: 0.16, metalness: 0, transparent: true, opacity: overFootage ? 0.94 : 0.66,
    clearcoat: 1, clearcoatRoughness: 0.05, ior: 1.5, specularIntensity: 1,
    sheen: 1, sheenColor: new THREE.Color("#FFFFFF"), sheenRoughness: 0.3,
    envMapIntensity: 1.4,
  }),
  accent: () => new THREE.MeshPhysicalMaterial({
    color: COLORS.orange, roughness: 0.28, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.08,
  }),
};

/* ---------- stage ---------- */

/**
 * createStage({ out, width, height, fov, exposure, shadowOpacity, fps })
 *   out: the visible 2D <canvas> the frames are drawn into (keep the brand stage behind it)
 */
export function createStage(opts) {
  const { out, width = 1080, height = 1920 } = opts;
  out.width = width; out.height = height;
  const ctx = out.getContext("2d");

  const gl = document.createElement("canvas");
  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = opts.exposure ?? 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.setClearColor(0xffffff, 0);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = opts.envIntensity ?? 1.0;

  const camera = new THREE.PerspectiveCamera(opts.fov ?? 28, width / height, 0.05, 500);

  const key = new THREE.DirectionalLight("#FFFFFF", opts.keyIntensity ?? 2.0);
  key.position.set(-3.5, 9, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.radius = 12;
  key.shadow.blurSamples = 16;
  key.shadow.bias = -0.0004;
  const sc = key.shadow.camera;
  sc.left = -8; sc.right = 8; sc.top = 8; sc.bottom = -8; sc.near = 0.5; sc.far = 40;
  const fill = new THREE.HemisphereLight("#FFFFFF", COLORS.ice, opts.fillIntensity ?? 0.5);
  scene.add(key, key.target, fill);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(80, 80),
    new THREE.ShadowMaterial({ color: COLORS.ink, opacity: opts.shadowOpacity ?? 0.16, depthWrite: false }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const stage = {
    THREE, renderer, scene, camera, key, fill, floor, width, height,
    focusTarget: new THREE.Vector3(),
    /** lens shift in pixels: positive y moves the subject up the frame without tilting the camera */
    shift(px) { camera.setViewOffset(width, height, 0, px, width, height); },
    /** world units per screen pixel at a distance d from the camera */
    unitsPerPixel(d) { return (2 * d * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2)) / height; },
    /** place the key light relative to the subject: high and slightly front-left, so the shadow sits under it */
    lightFrom(target, { x = -1.4, y = 10, z = 3 } = {}) {
      key.position.set(target.x + x, target.y + y, target.z + z);
      key.target.position.copy(target);
    },
    /**
     * Draw the frame at time t. update(t) must set every transform (camera included) from t alone.
     * cam: { samples: 1..16, shutter: 0.5, aperture: 0 }
     *   samples > 1 averages sub-frames: spread over the shutter (0.5 of a frame = 180°, motion blur)
     *   and over a lens disc of radius `aperture` in world units, focused on stage.focusTarget (depth of field).
     */
    frame(t, update, cam = {}, fps = opts.fps ?? 30) {
      const n = Math.max(1, Math.round(cam.samples ?? 1));
      const open = (cam.shutter ?? 0.5) / fps;
      const ap = n > 1 ? (cam.aperture ?? 0) : 0;
      const right = new THREE.Vector3(), up = new THREE.Vector3();
      for (let i = 0; i < n; i++) {
        const ts = n === 1 ? t : t - open / 2 + (open * i) / (n - 1);
        update(Math.max(0, ts));
        if (ap > 0) {
          // golden-angle disc: an even, deterministic spread of lens positions
          const r = ap * Math.sqrt((i + 0.5) / n), a = i * 2.399963;
          camera.updateMatrixWorld();
          right.setFromMatrixColumn(camera.matrixWorld, 0);
          up.setFromMatrixColumn(camera.matrixWorld, 1);
          camera.position.addScaledVector(right, r * Math.cos(a)).addScaledVector(up, r * Math.sin(a));
          camera.lookAt(stage.focusTarget);
        }
        renderer.render(scene, camera);
        ctx.globalCompositeOperation = i === 0 ? "copy" : "source-over";
        ctx.globalAlpha = i === 0 ? 1 : 1 / (i + 1);   // running mean of the sub-frames
        ctx.drawImage(gl, 0, 0);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
      update(t);
    },
  };
  return stage;
}

/* ---------- molecule (ball-and-stick) ---------- */

// Ball radius ≈ 0.25 × van der Waals radius (Å), the usual ball-and-stick proportion.
const BALL = { H: 0.30, C: 0.43, N: 0.39, O: 0.38, S: 0.45, P: 0.45, F: 0.37, Cl: 0.44 };
const CERAMIC_ELEMENTS = new Set(["C", "H"]);

/**
 * buildMolecule(data, { hydrogens, accent, overFootage })
 *   data: assets/molecules/<id>.json (atoms [el, x, y, z] in Å, bonds [i, j, order])
 *   Carbon and hydrogen are white ceramic, heteroatoms are frosted glass, and one atom
 *   (data.accent, or the accent option, or none with accent: false) is signal orange.
 *   Element is told apart by material and size, never by hue (no CPK blues and reds: §2).
 * Returns { group, radius, center, bottom }.
 */
export function buildMolecule(data, { hydrogens = true, accent, overFootage = false } = {}) {
  const accentIdx = accent === false ? -1 : (Number.isInteger(accent) ? accent : (data.accent ?? -1));
  const group = new THREE.Group();
  const keep = data.atoms.map((a) => hydrogens || a[0] !== "H");
  const mats = {
    ceramicC: materials.ceramic("#F2F4F7"),
    ceramicH: materials.ceramic("#FAFBFC"),
    frosted: materials.frosted(overFootage),
    accent: materials.accent(),
    bond: materials.ceramic("#E6EAF0"),
  };
  const sphere = new THREE.SphereGeometry(1, 48, 32);
  const pos = data.atoms.map((a) => new THREE.Vector3(a[1], a[2], a[3]));

  data.atoms.forEach((a, i) => {
    if (!keep[i]) return;
    const el = a[0];
    const mat = i === accentIdx ? mats.accent : CERAMIC_ELEMENTS.has(el) ? (el === "H" ? mats.ceramicH : mats.ceramicC) : mats.frosted;
    const m = new THREE.Mesh(sphere, mat);
    m.scale.setScalar(BALL[el] ?? 0.42);
    m.position.copy(pos[i]);
    m.castShadow = true;
    m.receiveShadow = true;
    group.add(m);
  });

  const cyl = new THREE.CylinderGeometry(1, 1, 1, 32, 1, false);
  const up = new THREE.Vector3(0, 1, 0);
  const addStick = (p, q, r, offset) => {
    const a = p.clone().add(offset), b = q.clone().add(offset);
    const dir = b.clone().sub(a);
    const m = new THREE.Mesh(cyl, mats.bond);
    m.scale.set(r, dir.length(), r);
    m.position.copy(a).addScaledVector(dir, 0.5);
    m.quaternion.setFromUnitVectors(up, dir.clone().normalize());
    m.castShadow = true;
    m.receiveShadow = true;
    group.add(m);
  };
  // a perpendicular for multiple bonds: in the plane of a neighbouring atom when there is one
  const neighbours = data.atoms.map(() => []);
  data.bonds.forEach(([i, j]) => { neighbours[i].push(j); neighbours[j].push(i); });
  const perpendicular = (i, j) => {
    const axis = pos[j].clone().sub(pos[i]).normalize();
    const k = neighbours[i].find((n) => n !== j) ?? neighbours[j].find((n) => n !== i);
    let ref = k !== undefined ? pos[k].clone().sub(pos[i]) : new THREE.Vector3(0, 0, 1);
    let v = ref.sub(axis.clone().multiplyScalar(ref.dot(axis)));
    if (v.lengthSq() < 1e-6) v = new THREE.Vector3(1, 0, 0).cross(axis);
    return v.normalize();
  };
  data.bonds.forEach(([i, j, order]) => {
    if (!keep[i] || !keep[j]) return;
    if (order === 1) return addStick(pos[i], pos[j], 0.11, new THREE.Vector3());
    const n = perpendicular(i, j);
    if (order === 2) {
      addStick(pos[i], pos[j], 0.075, n.clone().multiplyScalar(0.085));
      addStick(pos[i], pos[j], 0.075, n.clone().multiplyScalar(-0.085));
    } else if (order === 3) {
      addStick(pos[i], pos[j], 0.06, new THREE.Vector3());
      addStick(pos[i], pos[j], 0.06, n.clone().multiplyScalar(0.12));
      addStick(pos[i], pos[j], 0.06, n.clone().multiplyScalar(-0.12));
    } else {   // aromatic (1.5): one full stick plus a thinner partner
      addStick(pos[i], pos[j], 0.09, n.clone().multiplyScalar(0.05));
      addStick(pos[i], pos[j], 0.05, n.clone().multiplyScalar(-0.1));
    }
  });

  const box = new THREE.Box3().setFromObject(group);
  const sphereB = box.getBoundingSphere(new THREE.Sphere());
  // bottom: how far the lowest surface sits below the centre (a spin about the vertical axis keeps it)
  return { group, radius: sphereB.radius, center: sphereB.center, bottom: sphereB.center.y - box.min.y };
}

/* ---------- product photo (real packaging, label untouched) ---------- */

/** Load an image and find the bounding box of its opaque pixels (so padding never floats the pack). */
export async function loadCutout(url) {
  const img = await new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error(`could not load product photo: ${url}`));
    im.src = url;
  });
  const c = document.createElement("canvas");
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext("2d", { willReadFrequently: true });
  g.drawImage(img, 0, 0);
  const { data } = g.getImageData(0, 0, c.width, c.height);
  let x0 = c.width, y0 = c.height, x1 = -1, y1 = -1;
  for (let y = 0; y < c.height; y++) {
    for (let x = 0; x < c.width; x++) {
      if (data[(y * c.width + x) * 4 + 3] > 8) {
        if (x < x0) x0 = x; if (x > x1) x1 = x;
        if (y < y0) y0 = y; if (y > y1) y1 = y;
      }
    }
  }
  if (x1 < 0) throw new Error("product photo is fully transparent");
  const opaqueCorners = [0, c.width - 1].every((x) => [0, c.height - 1].every((y) => data[(y * c.width + x) * 4 + 3] > 250));
  return { img, w: c.width, h: c.height, box: { x0, y0, x1: x1 + 1, y1: y1 + 1 }, hasAlpha: !opaqueCorners };
}

/**
 * buildProduct(cutout, { height }): the photo on a plane standing on the floor (base at y = 0).
 *   The label pixels are drawn unlit and un-tonemapped, so packaging colours stay exactly as photographed.
 *   Realism comes from the light around it: a shadow cast by the pack's own silhouette, a soft contact
 *   shadow under the base and a faded floor reflection.
 */
export function buildProduct(cut, { height = 3, reflection = 0.16 } = {}) {
  const { box } = cut;
  const pw = box.x1 - box.x0, ph = box.y1 - box.y0;
  const width = (height * pw) / ph;
  const tex = new THREE.Texture(cut.img);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.repeat.set(pw / cut.w, ph / cut.h);
  tex.offset.set(box.x0 / cut.w, 1 - box.y1 / cut.h);
  tex.needsUpdate = true;

  const group = new THREE.Group();
  const geo = new THREE.PlaneGeometry(width, height);
  const photo = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
    map: tex, transparent: true, alphaTest: 0.02, toneMapped: false, side: THREE.DoubleSide,
  }));
  photo.position.y = height / 2;
  photo.castShadow = true;
  photo.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: tex, alphaTest: 0.5 });
  group.add(photo);

  // floor reflection: the photo mirrored under the base, fading out within ~30% of the pack height,
  // like a satin studio floor. alphaMap reads the GREEN channel, so the fade is drawn in grey levels.
  // The mirrored plane puts texture v = 0 (the pack's base) at the floor: the canvas bottom.
  if (reflection > 0) {
    const fade = document.createElement("canvas");
    fade.width = 4; fade.height = 256;
    const fg = fade.getContext("2d");
    const grd = fg.createLinearGradient(0, 0, 0, 256);
    grd.addColorStop(0, "#000000");
    grd.addColorStop(0.7, "#000000");
    grd.addColorStop(0.9, "#555555");
    grd.addColorStop(1, "#FFFFFF");
    fg.fillStyle = grd; fg.fillRect(0, 0, 4, 256);
    const alphaTex = new THREE.CanvasTexture(fade);
    const refl = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
      map: tex, alphaMap: alphaTex, transparent: true, opacity: reflection, toneMapped: false, depthWrite: false,
    }));
    refl.scale.y = -1;
    refl.renderOrder = -1;          // under the floor's shadow, as a reflection on a real floor is
    refl.position.y = -height / 2 - 0.002;
    group.add(refl);
  }

  // contact shadow: a soft ink ellipse right under the base (ambient occlusion where pack meets floor)
  const blob = document.createElement("canvas");
  blob.width = blob.height = 256;
  const bg = blob.getContext("2d");
  const rg = bg.createRadialGradient(128, 128, 0, 128, 128, 128);
  rg.addColorStop(0, "rgba(32,43,56,0.55)");
  rg.addColorStop(0.5, "rgba(32,43,56,0.18)");
  rg.addColorStop(1, "rgba(32,43,56,0)");
  bg.fillStyle = rg; bg.fillRect(0, 0, 256, 256);
  const blobTex = new THREE.CanvasTexture(blob);
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(width * 1.15, width * 0.32),
    new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, toneMapped: false, opacity: 0.6 }));
  contact.rotation.x = -Math.PI / 2;
  contact.position.y = 0.003;
  group.add(contact);

  return { group, width, height, photo };
}
