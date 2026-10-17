import fs from "fs";

const buf = fs.readFileSync(process.argv[2]);
const jsonLen = buf.readUInt32LE(12);
const gltf = JSON.parse(buf.subarray(20, 20 + jsonLen).toString("utf8"));
const nodes = gltf.nodes ?? [];

const parent = {};
nodes.forEach((n, i) => (n.children ?? []).forEach((c) => (parent[c] = i)));

const r = (v) => Math.round(v * 10) / 10;
const eulerDeg = ([x, y, z, w] = [0, 0, 0, 1]) => {
  const sinp = Math.max(-1, Math.min(1, 2 * (w * y - z * x)));
  return {
    x: r(
      (Math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)) * 180) /
        Math.PI,
    ),
    y: r((Math.asin(sinp) * 180) / Math.PI),
    z: r(
      (Math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) * 180) /
        Math.PI,
    ),
  };
};

const pubs = (o, acc = []) => {
  if (o && typeof o === "object") {
    if (o.pub?.output) {
      acc.push({
        output: o.pub.output,
        default: o.default,
        constraints: o.constraints,
      });
    }
    Object.values(o).forEach((v) => pubs(v, acc));
  }
  return acc;
};

const out = {};
nodes.forEach((n, i) => {
  if (!/eye|gaze|pupil|iris|look|lid/i.test(n.name ?? "")) return;
  const ancestors = [];
  for (let p = parent[i]; p !== undefined; p = parent[p])
    ancestors.push(nodes[p].name);
  out[n.name] = {
    translation: n.translation,
    rotationEulerDeg: eulerDeg(n.rotation),
    scale: n.scale,
    ancestors,
    inputs: pubs(n),
  };
});

console.log(
  JSON.stringify(Object.fromEntries(Object.entries(out).sort()), null, 2),
);

// print the parent's rotation
const p = nodes.find((n) => n.name === "Face_Tran_Rot_C");
console.log("Face_Tran_Rot_C", p?.translation, eulerDeg(p?.rotation), p?.scale);
