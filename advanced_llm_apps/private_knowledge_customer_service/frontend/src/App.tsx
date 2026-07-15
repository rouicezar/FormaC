import {
  Activity,
  AudioLines,
  Bot,
  Box,
  BrainCircuit,
  FileText,
  Image,
  Link,
  Loader2,
  MessageSquare,
  Plus,
  RadioTower,
  Search,
  Send,
  Sparkles,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

const API = import.meta.env.VITE_API_URL || "http://localhost:8897";

type Modality = "text" | "url" | "pdf" | "image" | "audio" | "video" | "query";

type RackPoint = {
  id: string;
  source_id: string;
  title: string;
  modality: Modality;
  projection: { x: number; y: number; z: number };
  color: string;
  preview?: string;
  score?: number;
};

type RackSource = {
  id: string;
  title: string;
  modality: Modality;
  summary: string;
  chunks: number;
  created_at: number;
  metadata?: Record<string, unknown>;
};

type SpaceSnapshot = {
  sources: RackSource[];
  points: RackPoint[];
  events: Array<Record<string, unknown>>;
  provider: string;
  dimensions: number;
  model: string;
  projection?: { method: string; basis: string };
};

type Match = {
  id: string;
  source_id: string;
  title: string;
  modality: Modality;
  text: string;
  score: number;
  projection: { x: number; y: number; z: number };
};

type AskResponse = {
  answer: string;
  matches: Match[];
  query_point: RackPoint;
  trace: Array<{ agent: string; status: string; detail: string }>;
  space: SpaceSnapshot;
};

const modalityIcon: Record<Modality, React.ElementType> = {
  text: FileText,
  url: Link,
  pdf: FileText,
  image: Image,
  audio: AudioLines,
  video: Video,
  query: Search,
};

const sampleText = `Gemini Embedding 2 可以将文本、图片、音频、视频和 PDF 映射到统一的语义向量空间。智能检索增强生成会先为知识片段生成向量，再检索与用户问题最相关的证据，并根据引用内容组织回答。`;

function scorePct(score: number) {
  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`;
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function indexFromId(id: string) {
  return Array.from(id).reduce((total, char) => total + char.charCodeAt(0), 0);
}

function cleanAnswerText(value: string) {
  return value
    .replace(/\[[a-f0-9]{8,12}-\d+\]/gi, "")
    .replace(/\*\*/g, "")
    .replace(/^\s*\*\s+/gm, "- ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function AnswerContent({ answer }: { answer: string }) {
  const cleaned = cleanAnswerText(answer);

  if (!cleaned) {
    return <p>检索到知识库证据后，回答会显示在这里。</p>;
  }

  const blocks = cleaned.split(/\n\s*\n/).filter(Boolean);
  return (
    <div className="answer-content">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        const isList = lines.length > 1 && lines.every((line) => line.startsWith("- "));
        const hasHeadingAndList =
          lines.length > 2 &&
          lines[0].endsWith(":") &&
          lines.slice(1).every((line) => line.startsWith("- "));
        if (isList) {
          return (
            <ul key={blockIndex}>
              {lines.map((line, lineIndex) => <li key={lineIndex}>{line.replace(/^- /, "")}</li>)}
            </ul>
          );
        }
        if (hasHeadingAndList) {
          return (
            <div className="answer-section" key={blockIndex}>
              <h3>{lines[0].replace(/:$/, "")}</h3>
              <ul>
                {lines.slice(1).map((line, lineIndex) => <li key={lineIndex}>{line.replace(/^- /, "")}</li>)}
              </ul>
            </div>
          );
        }
        return lines.map((line, lineIndex) => {
          if (line.endsWith(":") && line.length < 48) {
            return <h3 key={`${blockIndex}-${lineIndex}`}>{line.replace(/:$/, "")}</h3>;
          }
          if (line.startsWith("- ")) {
            return <ul key={`${blockIndex}-${lineIndex}`}><li>{line.replace(/^- /, "")}</li></ul>;
          }
          return <p key={`${blockIndex}-${lineIndex}`}>{line}</p>;
        });
      })}
    </div>
  );
}

function makeGlowTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  if (!context) return new THREE.Texture();

  const gradient = context.createRadialGradient(64, 64, 3, 64, 64, 62);
  gradient.addColorStop(0, "rgba(255,255,255,0.95)");
  gradient.addColorStop(0.22, "rgba(255,255,255,0.48)");
  gradient.addColorStop(0.58, "rgba(255,255,255,0.14)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 128, 128);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function VectorSpace({
  points,
  queryPoint,
  matches,
  selectedId,
  onSelect,
}: {
  points: RackPoint[];
  queryPoint: RackPoint | null;
  matches: Match[];
  selectedId: string | null;
  onSelect: (point: RackPoint | null) => void;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const pointMapRef = useRef<Map<string, RackPoint>>(new Map());
  const selectedIdRef = useRef<string | null>(selectedId);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    if (!mountRef.current) return;

    const mount = mountRef.current;
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x070806, 9, 26);

    const camera = new THREE.PerspectiveCamera(48, mount.clientWidth / mount.clientHeight, 0.1, 100);
    camera.position.set(0, 1.9, 9.2);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const frameGroup = new THREE.Group();
    const pointGroup = new THREE.Group();
    scene.add(frameGroup);
    scene.add(pointGroup);

    const grid = new THREE.GridHelper(10, 20, 0xf54e00, 0x303126);
    grid.position.y = -2.8;
    grid.material.opacity = 0.28;
    grid.material.transparent = true;
    frameGroup.add(grid);

    const axes = [
      [new THREE.Vector3(-4.8, -2.6, -2.8), new THREE.Vector3(4.8, -2.6, -2.8), 0xf54e00],
      [new THREE.Vector3(-4.8, -2.6, -2.8), new THREE.Vector3(-4.8, 2.8, -2.8), 0x9fc9a2],
      [new THREE.Vector3(-4.8, -2.6, -2.8), new THREE.Vector3(-4.8, -2.6, 2.8), 0x9fbbe0],
    ] as const;
    axes.forEach(([start, end, color]) => {
      const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
      const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 });
      frameGroup.add(new THREE.Line(geometry, material));
    });

    const backdropGeometry = new THREE.BufferGeometry();
    const backdropPositions = new Float32Array(150 * 3);
    for (let index = 0; index < 150; index += 1) {
      backdropPositions[index * 3] = (Math.random() - 0.5) * 12;
      backdropPositions[index * 3 + 1] = (Math.random() - 0.5) * 7;
      backdropPositions[index * 3 + 2] = (Math.random() - 0.5) * 9;
    }
    backdropGeometry.setAttribute("position", new THREE.BufferAttribute(backdropPositions, 3));
    const backdrop = new THREE.Points(
      backdropGeometry,
      new THREE.PointsMaterial({ color: 0xf7f7f4, size: 0.012, transparent: true, opacity: 0.34 })
    );
    frameGroup.add(backdrop);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const pointerTarget = new THREE.Vector2();
    const meshes: THREE.Mesh[] = [];
    const halos: THREE.Sprite[] = [];
    const objectsById = new Map<string, { halo?: THREE.Sprite; base: THREE.Vector3; orbit: number; phase: number; speed: number }>();
    const matchedIds = new Set(matches.map((match) => match.source_id));
    const glowTexture = makeGlowTexture();
    const allPoints = queryPoint ? [...points, queryPoint] : points;
    pointMapRef.current = new Map(allPoints.map((point) => [point.id, point]));

    allPoints.forEach((point) => {
      const position = new THREE.Vector3(point.projection.x * 1.35, point.projection.y * 1.35, point.projection.z * 1.35);
      const isQuery = point.modality === "query";
      const isMatched = matchedIds.has(point.source_id);
      if (isQuery || isMatched) {
        const haloMaterial = new THREE.SpriteMaterial({
          map: glowTexture,
          color: new THREE.Color(isQuery ? "#f54e00" : point.color),
          transparent: true,
          opacity: isQuery ? 0.32 : 0.24,
          depthWrite: false,
        });
        const halo = new THREE.Sprite(haloMaterial);
        halo.position.copy(position);
        halo.scale.setScalar(isQuery ? 0.72 : 0.58);
        halo.userData.baseScale = isQuery ? 0.72 : 0.58;
        halo.userData.baseOpacity = isQuery ? 0.32 : 0.24;
        halo.userData.id = point.id;
        halos.push(halo);
        pointGroup.add(halo);
      }

      const geometry = new THREE.SphereGeometry(0.08, 24, 24);
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color(point.color),
        transparent: true,
        opacity: point.modality === "query" ? 1 : 0.9,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(position);
      mesh.userData.id = point.id;
      meshes.push(mesh);
      pointGroup.add(mesh);
      objectsById.set(point.id, {
        halo: halos.find((item) => item.userData.id === point.id),
        base: position,
        orbit: isQuery ? 0.028 : 0.075 + (indexFromId(point.id) % 5) * 0.012,
        phase: (indexFromId(point.id) % 13) * 0.62,
        speed: isQuery ? 0.28 : 0.34 + (indexFromId(point.id) % 7) * 0.035,
      });
    });

    const handlePointer = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      pointerTarget.set(pointer.x, pointer.y);
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(meshes)[0];
      renderer.domElement.style.cursor = hit ? "pointer" : "default";
      onSelect(hit ? pointMapRef.current.get(hit.object.userData.id) ?? null : null);
    };

    const handlePointerLeave = () => {
      pointerTarget.set(0, 0);
      renderer.domElement.style.cursor = "default";
      onSelect(null);
    };

    renderer.domElement.addEventListener("pointermove", handlePointer);
    renderer.domElement.addEventListener("pointerleave", handlePointerLeave);

    const resize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", resize);

    let frame = 0;
    let animation = 0;
    const animate = () => {
      frame += 0.01;
      camera.position.x += (pointerTarget.x * 0.18 - camera.position.x) * 0.025;
      camera.position.y += (1.9 + pointerTarget.y * 0.1 - camera.position.y) * 0.025;
      camera.lookAt(0, 0, 0);
      meshes.forEach((mesh, index) => {
        const object = objectsById.get(mesh.userData.id);
        if (object) {
          const theta = frame * object.speed + object.phase;
          const bob = Math.sin(frame * object.speed * 1.7 + object.phase) * object.orbit * 0.48;
          mesh.position.set(
            object.base.x + Math.cos(theta) * object.orbit,
            object.base.y + bob,
            object.base.z + Math.sin(theta) * object.orbit
          );
          mesh.rotation.y += 0.012 + index * 0.0004;
          mesh.rotation.x += 0.006;
          object.halo?.position.copy(mesh.position);
        }
        const pulse = 1 + Math.sin(frame * 2.2 + index) * 0.055;
        mesh.scale.setScalar(mesh.userData.id === selectedIdRef.current ? 1.22 : pulse);
      });
      halos.forEach((halo, index) => {
        const base = halo.userData.baseScale || 0.58;
        const pulse = 1 + Math.sin(frame * 1.7 + index) * 0.08;
        halo.scale.setScalar(base * pulse);
        const material = halo.material as THREE.SpriteMaterial;
        material.opacity = halo.userData.id === selectedIdRef.current ? 0.46 : halo.userData.baseOpacity;
      });
      renderer.render(scene, camera);
      animation = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(animation);
      window.removeEventListener("resize", resize);
      renderer.domElement.removeEventListener("pointermove", handlePointer);
      renderer.domElement.removeEventListener("pointerleave", handlePointerLeave);
      mount.removeChild(renderer.domElement);
      glowTexture.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) object.material.forEach((material) => material.dispose());
          else object.material.dispose();
        }
        if (object instanceof THREE.Sprite) {
          object.material.dispose();
        }
      });
      renderer.dispose();
    };
  }, [points, queryPoint, matches, onSelect]);

  return <div className="vector-canvas" ref={mountRef} />;
}

function SourceRow({
  source,
  isRemoving,
  onRemove,
}: {
  source: RackSource;
  isRemoving: boolean;
  onRemove: (source: RackSource) => void;
}) {
  const Icon = modalityIcon[source.modality] || Box;
  const embeddingPath = String(source.metadata?.embedding_path || "");
  return (
    <div className="source-row">
      <div className={`modality-dot ${source.modality}`}>
        <Icon size={15} />
      </div>
      <div className="source-copy">
        <div className="source-title">{source.title}</div>
        <div className="source-summary">{source.summary}</div>
        {embeddingPath && <div className="source-meta">{embeddingPath.replace("gemini-", "Gemini ")}</div>}
      </div>
      <div className="source-actions">
        <button className="delete-source" onClick={() => onRemove(source)} disabled={isRemoving} aria-label={`移除 ${source.title}`}>
          {isRemoving ? <Loader2 className="spin" size={13} /> : <Trash2 size={13} />}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [space, setSpace] = useState<SpaceSnapshot | null>(null);
  const [tab, setTab] = useState<"text" | "url" | "file">("text");
  const [title, setTitle] = useState("知识库示例说明");
  const [text, setText] = useState(sampleText);
  const [url, setUrl] = useState("https://developers.googleblog.com/building-with-gemini-embedding-2/");
  const [notes, setNotes] = useState("知识来源补充说明");
  const [question, setQuestion] = useState("知识库如何基于文档回答问题？");
  const [answer, setAnswer] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);
  const [trace, setTrace] = useState<AskResponse["trace"]>([]);
  const [queryPoint, setQueryPoint] = useState<RackPoint | null>(null);
  const [selectedPoint, setSelectedPoint] = useState<RackPoint | null>(null);
  const [isAddingSource, setIsAddingSource] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [removingSourceId, setRemovingSourceId] = useState<string | null>(null);
  const [sourceStatus, setSourceStatus] = useState("");
  const [sourceError, setSourceError] = useState("");
  const [qaStatus, setQaStatus] = useState("");
  const [qaError, setQaError] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const points = useMemo(() => space?.points ?? [], [space]);
  const sourceCount = space?.sources.length ?? 0;
  const pointCount = space?.points.length ?? 0;
  const provider = space?.provider ?? "正在连接";
  const projection = space?.projection?.method?.replace("_", " ").toUpperCase() ?? "PCA 3D";

  async function refreshSpace() {
    const res = await fetch(`${API}/space`);
    setSpace(await res.json());
  }

  useEffect(() => {
    refreshSpace().catch(() => undefined);
  }, []);

  async function addSource() {
    setIsAddingSource(true);
    setSourceError("");
    setSourceStatus(tab === "file" ? "正在处理文件并建立索引……" : "正在建立知识索引……");
    try {
      let res: Response;
      if (tab === "text") {
        res = await fetch(`${API}/sources/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, text, modality: "text" }),
        });
      } else if (tab === "url") {
        res = await fetch(`${API}/sources/url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, title: title || undefined }),
        });
      } else {
        const file = fileRef.current?.files?.[0];
        if (!file) {
          setSourceError("请先选择文件。");
          return;
        }
        const form = new FormData();
        form.append("title", title || file.name);
        form.append("file", file);
        form.append("notes", notes);
        res = await fetch(`${API}/sources/file`, { method: "POST", body: form });
      }

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "知识来源处理失败。");
      setSpace(data.space);
      setSourceStatus(`${data.source?.title || "知识来源"} 已建立索引。`);
    } catch (error) {
      setSourceError(error instanceof Error ? error.message : "知识来源处理失败。");
    } finally {
      setIsAddingSource(false);
    }
  }

  async function removeSource(source: RackSource) {
    const confirmed = window.confirm(`确认从本地知识库中移除“${source.title}”吗？`);
    if (!confirmed) return;

    setRemovingSourceId(source.id);
    setSourceError("");
    try {
      const res = await fetch(`${API}/sources/${source.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("删除失败");
      const data = await res.json();
      setSpace(data.space);
      setMatches((current) => current.filter((match) => match.source_id !== source.id));
      if (selectedPoint?.source_id === source.id) setSelectedPoint(null);
      if (queryPoint) setQueryPoint(null);
      setSourceStatus(`${source.title} 已移除。`);
    } catch (error) {
      setSourceError(error instanceof Error ? error.message : "删除失败。" );
    } finally {
      setRemovingSourceId(null);
    }
  }

  async function askQuestion() {
    if (!question.trim()) return;
    setIsAsking(true);
    setQaError("");
    setQaStatus("正在检索知识证据并组织回答……");
    setAnswer("");
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 6 }),
      });
      const data: AskResponse = await res.json();
      if (!res.ok) throw new Error((data as unknown as { detail?: string }).detail || "提问失败。" );
      setAnswer(data.answer);
      setMatches(data.matches);
      setTrace(data.trace);
      setQueryPoint(data.query_point);
      setSpace(data.space);
      setQaStatus(`已检索到 ${data.matches.length} 条引用。`);
    } catch (error) {
      setQaError(error instanceof Error ? error.message : "处理问题时发生错误。" );
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <BrainCircuit size={22} />
          </div>
          <div>
            <h1>私有知识库问答</h1>
            <p>本地知识索引 · 可核查引用</p>
          </div>
        </div>
        <div className="status-strip">
          <span><RadioTower size={14} /> {provider}</span>
          <span><Box size={14} /> {pointCount} 个索引点</span>
          <span><Activity size={14} /> {sourceCount} 个知识来源</span>
        </div>
      </header>

      <section className="workspace">
        <aside className="left-rail">
          <section className="panel source-list">
            <div className="panel-heading source-list-heading">
              <div>
                <h2>已索引知识来源</h2>
                <p>查看当前进入知识库的内容。</p>
              </div>
            </div>
            {space?.sources.map((source) => (
              <SourceRow
                source={source}
                key={source.id}
                isRemoving={removingSourceId === source.id}
                onRemove={removeSource}
              />
            ))}
          </section>

          <section className="panel source-panel">
            <div className="panel-heading">
              <div>
                <h2>知识来源</h2>
                <p>当前为复用模板预览，后续改为本地目录扫描。</p>
              </div>
              <button className="icon-button" onClick={refreshSpace} aria-label="刷新知识索引状态">
                <Activity size={16} />
              </button>
            </div>

            <div className="tabs" role="tablist">
              <button className={tab === "text" ? "active" : ""} onClick={() => setTab("text")}><FileText size={14} /> 文本</button>
              <button className={tab === "url" ? "active" : ""} onClick={() => setTab("url")}><Link size={14} /> 网页地址</button>
              <button className={tab === "file" ? "active" : ""} onClick={() => setTab("file")}><Upload size={14} /> 文件</button>
            </div>

            <label className="field-label">标题</label>
            <input value={title} onChange={(event) => setTitle(event.target.value)} aria-label="知识来源标题" />

            {tab === "text" && (
              <>
                <label className="field-label">知识原文</label>
                <textarea value={text} onChange={(event) => setText(event.target.value)} aria-label="知识原文" />
              </>
            )}

            {tab === "url" && (
              <>
                <label className="field-label">网页地址</label>
                <input value={url} onChange={(event) => setUrl(event.target.value)} aria-label="知识来源网页地址" />
              </>
            )}

            {tab === "file" && (
              <>
                <label className="field-label">文件</label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.md,.pdf,image/*,audio/*,video/*"
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setSelectedFile(file);
                    if (file && title === "知识库示例说明") setTitle(file.name);
                  }}
                />
                {selectedFile && (
                  <div className="file-preview">
                    <Video size={15} />
                    <span>{selectedFile.name}</span>
                    <strong>{selectedFile.type || "文件"} · {formatBytes(selectedFile.size)}</strong>
                  </div>
                )}
                <label className="field-label">补充说明</label>
                <textarea value={notes} onChange={(event) => setNotes(event.target.value)} aria-label="文件补充说明" />
              </>
            )}

            <button className="primary-button" onClick={addSource} disabled={isAddingSource}>
              {isAddingSource ? <Loader2 className="spin" size={16} /> : <Plus size={16} />} 添加知识来源
            </button>
            {(sourceStatus || sourceError) && (
              <div className={`inline-status ${sourceError ? "error" : "success"}`} role="status">
                {sourceError || sourceStatus}
              </div>
            )}
          </section>
        </aside>

        <section className="space-stage">
          <div className="stage-header">
            <div>
              <h2>知识索引空间</h2>
              <p>{space?.dimensions ?? 768} 维向量 · {projection} · 每个知识来源对应一个索引点</p>
            </div>
            <div className="stage-tools">
              <div className="modality-key" aria-label="知识类型图例">
                {([['Text', '文本'], ['Image', '图片'], ['Audio', '音频'], ['Video', '视频'], ['PDF', 'PDF'], ['Query', '问题']] as const).map(([key, label]) => (
                  <span key={key} className={`modality-key-item key-${key.toLowerCase()}`}>{label}</span>
                ))}
              </div>
              <div className="space-readout" aria-label="知识索引状态">
                <span>{sourceCount} 个来源</span>
                <span>{matches.length ? `匹配 ${matches.length} 条` : "就绪"}</span>
              </div>
            </div>
          </div>
          <VectorSpace
            points={points}
            queryPoint={queryPoint}
            matches={matches}
            selectedId={selectedPoint?.id ?? null}
            onSelect={setSelectedPoint}
          />
          {selectedPoint && (
            <div className="hover-card">
              <div className={`mini-dot ${selectedPoint.modality}`} />
              <strong>{selectedPoint.title}</strong>
              <span>{selectedPoint.modality} · {selectedPoint.id}</span>
              <p>{selectedPoint.preview}</p>
            </div>
          )}
        </section>

        <aside className="right-rail">
          <section className="panel qa-panel">
            <div className="panel-heading">
              <div>
                <h2>知识问答</h2>
                <p>用自然语言提问，查看基于知识库的回答。</p>
              </div>
              <Bot size={18} />
            </div>
            <label className="field-label">问题</label>
            <textarea className="question-box" value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="请输入问题" />
            <button className="primary-button" onClick={askQuestion} disabled={isAsking}>
              {isAsking ? <Loader2 className="spin" size={16} /> : <Send size={16} />} 开始提问
            </button>
            {(qaStatus || qaError) && (
              <div className={`inline-status ${qaError ? "error" : "success"}`} role="status">
                {qaError || qaStatus}
              </div>
            )}
            <div className="answer-box prominent-answer">
              <MessageSquare size={16} />
              <AnswerContent answer={answer} />
            </div>
          </section>

          <section className="panel trace-panel">
            <div className="panel-heading">
              <div>
                <h2>处理过程</h2>
                <p>知识检索与回答步骤</p>
              </div>
              <Sparkles size={18} />
            </div>
            <div className="trace-list">
              {(trace.length ? trace : [
                { agent: "知识来源", status: "ready", detail: "等待用户提问" },
                { agent: "知识检索", status: "ready", detail: "检索到的相关证据会显示在这里" },
                { agent: "回答生成", status: "ready", detail: "根据引用证据组织回答" },
              ]).map((step) => (
                <div className="trace-row" key={step.agent}>
                  <span>{step.agent}</span>
                  <p>{step.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel citations-panel">
            <div className="panel-heading">
              <div>
                <h2>引用来源</h2>
                <p>本次回答使用的知识证据</p>
              </div>
            </div>
            <div className="citation-list">
              {matches.length === 0 && <div className="empty-state">还没有检索记录。完成知识扫描后即可开始提问。</div>}
              {matches.map((match) => {
                const Icon = modalityIcon[match.modality] || FileText;
                return (
                  <button
                    className="citation-row"
                    key={match.id}
                    onMouseEnter={() => setSelectedPoint({ ...match, color: "#f54e00", preview: match.text })}
                    onMouseLeave={() => setSelectedPoint(null)}
                  >
                    <div className="citation-top">
                      <span><Icon size={14} /> {match.title}</span>
                      <strong>{scorePct(match.score)}</strong>
                    </div>
                    <div className="score-track" aria-hidden="true"><div style={{ width: scorePct(match.score) }} /></div>
                    <p>{match.text}</p>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
