'use client';

/**
 * GraphRAG Knowledge Graph Visualization
 * Interactive force-directed graph showing drug-payer-indication relationships
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, RotateCcw, Sparkles } from 'lucide-react';

interface GraphNode {
  id: string;
  label: string;
  type: 'drug' | 'payer' | 'indication' | 'llm';
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  size: number;
}

interface GraphEdge {
  source: string;
  target: string;
  type: 'covers' | 'restricts' | 'requires' | 'treats';
}

// Node colors matching the reference image
const NODE_COLORS = {
  drug: '#f472b4', // Pink (center LLM node style)
  payer: '#fbbf24', // Amber/Yellow
  indication: '#22d3ee', // Cyan
  llm: '#f472b4', // Pink
};

const PAYER_COLORS: Record<string, string> = {
  UHC: '#16a34a', // Green - covered
  Cigna: '#d97706', // Amber - conditional
  BCBS: '#16a34a', // Green - covered
  Aetna: '#dc2626', // Red - restricted
};

// Build knowledge graph from drug data
const buildGraphData = () => {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  // Central LLM/Drug node
  nodes.push({
    id: 'rituximab',
    label: 'Rituximab',
    type: 'drug',
    x: 400,
    y: 250,
    vx: 0,
    vy: 0,
    color: NODE_COLORS.drug,
    size: 45,
  });

  // Payer nodes positioned around the drug
  const payers = [
    { id: 'uhc', label: 'UHC', angle: -45 },
    { id: 'cigna', label: 'Cigna', angle: 45 },
    { id: 'bcbs', label: 'BCBS', angle: 135 },
    { id: 'aetna', label: 'Aetna', angle: 225 },
  ];

  payers.forEach((payer, i) => {
    const angle = (payer.angle * Math.PI) / 180;
    const radius = 150;
    nodes.push({
      id: payer.id,
      label: payer.label,
      type: 'payer',
      x: 400 + Math.cos(angle) * radius,
      y: 250 + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
      color: PAYER_COLORS[payer.label] || NODE_COLORS.payer,
      size: 35,
    });
    edges.push({ source: 'rituximab', target: payer.id, type: 'covers' });
  });

  // Indication nodes
  const indications = [
    { id: 'ra', label: 'RA', angle: 0 },
    { id: 'nhl', label: 'NHL', angle: 72 },
    { id: 'cll', label: 'CLL', angle: 144 },
    { id: 'gpa', label: 'GPA', angle: 216 },
    { id: 'pv', label: 'PV', angle: 288 },
  ];

  indications.forEach((ind) => {
    const angle = (ind.angle * Math.PI) / 180;
    const radius = 280;
    nodes.push({
      id: ind.id,
      label: ind.label,
      type: 'indication',
      x: 400 + Math.cos(angle) * radius,
      y: 250 + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
      color: NODE_COLORS.indication,
      size: 25,
    });
  });

  // Connect payers to their covered indications
  // UHC: RA, NHL, CLL, GPA
  ['ra', 'nhl', 'cll', 'gpa'].forEach((ind) => {
    edges.push({ source: 'uhc', target: ind, type: 'covers' });
  });

  // Cigna: NHL, CLL only
  ['nhl', 'cll'].forEach((ind) => {
    edges.push({ source: 'cigna', target: ind, type: 'covers' });
  });

  // BCBS: RA, NHL, CLL, GPA, PV
  ['ra', 'nhl', 'cll', 'gpa', 'pv'].forEach((ind) => {
    edges.push({ source: 'bcbs', target: ind, type: 'covers' });
  });

  // Aetna: NHL only
  edges.push({ source: 'aetna', target: 'nhl', type: 'restricts' });

  return { nodes, edges };
};

export function GraphRAGVisualization() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [graphData, setGraphData] = useState(buildGraphData);
  const [isSimulating, setIsSimulating] = useState(false); // Start paused for better performance
  const [isInitialized, setIsInitialized] = useState(false);

  // Simple force simulation
  const simulate = useCallback(() => {
    if (!isSimulating) return;

    setGraphData((prev) => {
      const nodes = [...prev.nodes];
      const edges = prev.edges;

      // Apply forces
      nodes.forEach((node) => {
        // Repulsion from other nodes
        nodes.forEach((other) => {
          if (node.id === other.id) return;
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 500 / (dist * dist);
          node.vx += (dx / dist) * force * 0.1;
          node.vy += (dy / dist) * force * 0.1;
        });

        // Attraction to connected nodes
        edges.forEach((edge) => {
          let other: GraphNode | undefined;
          if (edge.source === node.id) {
            other = nodes.find((n) => n.id === edge.target);
          } else if (edge.target === node.id) {
            other = nodes.find((n) => n.id === edge.source);
          }
          if (other) {
            const dx = other.x - node.x;
            const dy = other.y - node.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - 120) * 0.01;
            node.vx += (dx / dist) * force;
            node.vy += (dy / dist) * force;
          }
        });

        // Center gravity
        node.vx += (400 - node.x) * 0.001;
        node.vy += (250 - node.y) * 0.001;

        // Friction
        node.vx *= 0.9;
        node.vy *= 0.9;

        // Update position
        node.x += node.vx;
        node.y += node.vy;

        // Bounds
        node.x = Math.max(50, Math.min(750, node.x));
        node.y = Math.max(50, Math.min(450, node.y));
      });

      return { nodes, edges };
    });
  }, [isSimulating]);

  // Draw the graph
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { nodes, edges } = graphData;

    // Clear with gradient background
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#1e3a5f');
    gradient.addColorStop(0.5, '#2d1b4e');
    gradient.addColorStop(1, '#3730a3');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Apply zoom
    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.scale(zoom, zoom);
    ctx.translate(-canvas.width / 2, -canvas.height / 2);

    // Draw edges
    edges.forEach((edge) => {
      const sourceNode = nodes.find((n) => n.id === edge.source);
      const targetNode = nodes.find((n) => n.id === edge.target);
      if (sourceNode && targetNode) {
        ctx.beginPath();
        ctx.moveTo(sourceNode.x, sourceNode.y);
        ctx.lineTo(targetNode.x, targetNode.y);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    // Draw nodes
    nodes.forEach((node) => {
      const isHovered = hoveredNode?.id === node.id;
      const size = isHovered ? node.size * 1.2 : node.size;

      // Glow effect
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 10, 0, Math.PI * 2);
        ctx.fillStyle = `${node.color}40`;
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();

      // Node label
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${node.type === 'drug' ? 14 : 11}px IBM Plex Sans, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.label, node.x, node.y);
    });

    ctx.restore();
  }, [graphData, zoom, hoveredNode]);

  // Initial draw on mount
  useEffect(() => {
    if (!isInitialized) {
      draw();
      setIsInitialized(true);
    }
  }, [draw, isInitialized]);

  // Animation loop - only runs when isSimulating is true
  useEffect(() => {
    if (!isSimulating) {
      // Just draw once when paused
      draw();
      return;
    }

    const loop = () => {
      simulate();
      draw();
      animationRef.current = requestAnimationFrame(loop);
    };
    animationRef.current = requestAnimationFrame(loop);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [simulate, draw, isSimulating]);

  // Redraw when zoom or hover changes (when paused)
  useEffect(() => {
    if (!isSimulating) {
      draw();
    }
  }, [zoom, hoveredNode, draw, isSimulating]);

  // Handle mouse move for hover effects
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);

    const { nodes } = graphData;
    const hovered = nodes.find((node) => {
      const dx = x - node.x;
      const dy = y - node.y;
      return Math.sqrt(dx * dx + dy * dy) < node.size;
    });

    setHoveredNode(hovered || null);
  };

  const resetGraph = () => {
    setGraphData(buildGraphData());
    setZoom(1);
  };

  return (
    <Card className="overflow-hidden border-border-light bg-card">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-accent-blue" />
          <CardTitle className="text-lg font-semibold text-ink">
            Knowledge Graph — Drug Policy Relationships
          </CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2))}
            className="h-8 w-8 p-0"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.5))}
            className="h-8 w-8 p-0"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={resetGraph}
            className="h-8 w-8 p-0"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button
            variant={isSimulating ? 'default' : 'outline'}
            size="sm"
            onClick={() => setIsSimulating(!isSimulating)}
            className="h-8 px-3 text-xs"
          >
            {isSimulating ? 'Pause' : 'Animate Graph'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="relative">
          <canvas
            ref={canvasRef}
            width={800}
            height={500}
            className="w-full h-[400px] cursor-pointer"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoveredNode(null)}
          />

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex flex-wrap gap-3 bg-white/90 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#f472b4]" />
              <span className="text-xs text-ink">Drug</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#fbbf24]" />
              <span className="text-xs text-ink">Payer</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#22d3ee]" />
              <span className="text-xs text-ink">Indication</span>
            </div>
          </div>

          {/* Hover tooltip */}
          {hoveredNode && (
            <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-sm rounded-lg px-4 py-3 shadow-md max-w-[200px]">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: hoveredNode.color }}
                />
                <span className="font-semibold text-ink">{hoveredNode.label}</span>
              </div>
              <Badge variant="secondary" className="text-xs capitalize">
                {hoveredNode.type}
              </Badge>
            </div>
          )}
        </div>

        {/* AI Insight */}
        <div className="px-6 py-4 bg-accent-blue/5 border-t border-border-light">
          <div className="flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-accent-blue mt-0.5" />
            <div>
              <p className="text-sm text-ink font-medium mb-1">AI Insight</p>
              <p className="text-sm text-muted-text">
                BCBS has the broadest indication coverage for Rituximab, including PV which other payers restrict. 
                Aetna shows the most restrictive policy with NHL-only coverage and 3 prior drug requirements.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
