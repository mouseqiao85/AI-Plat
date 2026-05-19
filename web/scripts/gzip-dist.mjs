import { createGzip } from "node:zlib";
import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, readdir, stat } from "node:fs/promises";
import { extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { pipeline } from "node:stream/promises";

const distDir = fileURLToPath(new URL("../dist/", import.meta.url));
const compressible = new Set([".css", ".html", ".js", ".json", ".svg", ".txt", ".xml"]);

let compressedCount = 0;

async function gzipFile(path) {
  const input = await stat(path);
  if (input.size < 1024) return;
  await pipeline(
    createReadStream(path),
    createGzip({ level: 9 }),
    createWriteStream(`${path}.gz`),
  );
  compressedCount += 1;
}

async function walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(path);
    } else if (!entry.name.endsWith(".gz") && compressible.has(extname(entry.name))) {
      await gzipFile(path);
    }
  }
}

await mkdir(distDir, { recursive: true });
await walk(distDir);
console.log(`Generated ${compressedCount} gzip assets`);
