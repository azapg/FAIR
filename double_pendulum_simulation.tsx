import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Pause, RotateCcw, Activity, Settings, Info } from 'lucide-react';

export default function App() {
  // Configurable physics parameters
  const [params, setParams] = useState({
    m1: 15,    // Mass of pendulum 1
    m2: 15,    // Mass of pendulum 2
    l1: 140,   // Length of pendulum 1
    l2: 140,   // Length of pendulum 2
    g: 2.0     // Gravity
  });

  const [isPlaying, setIsPlaying] = useState(true);
  const [showInfo, setShowInfo] = useState(false);

  // Refs for animation loop & canvas mapping
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const requestRef = useRef();
  
  // Use refs for parameters & state to avoid stale closures in the animation loop
  const paramsRef = useRef(params);
  const playRef = useRef(isPlaying);
  
  const simRef = useRef({
    theta1: Math.PI / 2,
    theta2: Math.PI / 2,
    omega1: 0,
    omega2: 0,
    trail: [],
    dragging: 0, // 0: none, 1: mass1, 2: mass2
    frame: 0,
    originX: 0,
    originY: 0
  });

  // Keep refs synchronized with React state
  useEffect(() => { paramsRef.current = params; }, [params]);
  useEffect(() => { playRef.current = isPlaying; }, [isPlaying]);

  // Main Physics & Render Loop
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const sim = simRef.current;
    const p = paramsRef.current;

    // ----- PHYSICS ENGINE -----
    // If playing and not actively being dragged by user, update physics
    if (playRef.current && sim.dragging === 0) {
      const dt = 0.15; // Base time step
      const subSteps = 10; // Sub-stepping for integration stability (vital for chaotic systems)
      const subDt = dt / subSteps;

      for (let i = 0; i < subSteps; i++) {
        const t1 = sim.theta1;
        const t2 = sim.theta2;
        const w1 = sim.omega1;
        const w2 = sim.omega2;
        
        // Complex Lagrangian Equations of Motion for a Double Pendulum
        const delta = t1 - t2;
        
        const num1 = -p.g * (2 * p.m1 + p.m2) * Math.sin(t1);
        const num2 = -p.m2 * p.g * Math.sin(t1 - 2 * t2);
        const num3 = -2 * Math.sin(delta) * p.m2 * (w2 * w2 * p.l2 + w1 * w1 * p.l1 * Math.cos(delta));
        const den1 = p.l1 * (2 * p.m1 + p.m2 - p.m2 * Math.cos(2 * t1 - 2 * t2));
        const alpha1 = (num1 + num2 + num3) / den1;

        const num4 = 2 * Math.sin(delta) * (w1 * w1 * p.l1 * (p.m1 + p.m2) + p.g * (p.m1 + p.m2) * Math.cos(t1) + w2 * w2 * p.l2 * p.m2 * Math.cos(delta));
        const den2 = p.l2 * (2 * p.m1 + p.m2 - p.m2 * Math.cos(2 * t1 - 2 * t2));
        const alpha2 = num4 / den2;

        // Semi-implicit Euler integration
        sim.omega1 += alpha1 * subDt;
        sim.omega2 += alpha2 * subDt;
        sim.theta1 += sim.omega1 * subDt;
        sim.theta2 += sim.omega2 * subDt;
      }
      
      // Apply very slight damping so it doesn't spin wildly forever if energy gets high
      sim.omega1 *= 0.9995;
      sim.omega2 *= 0.9995;
    }

    // Calculate Cartesian coordinates of the masses
    const x1 = sim.originX + p.l1 * Math.sin(sim.theta1);
    const y1 = sim.originY + p.l1 * Math.cos(sim.theta1);
    const x2 = x1 + p.l2 * Math.sin(sim.theta2);
    const y2 = y1 + p.l2 * Math.cos(sim.theta2);

    // Update trail (only if moving)
    if (playRef.current || sim.dragging !== 0) {
      sim.trail.push({ x: x2, y: y2, hue: sim.frame % 360 });
      // Cap the trail length to prevent performance drops
      if (sim.trail.length > 300) {
        sim.trail.shift();
      }
    }
    
    sim.frame += 1;

    // ----- RENDERING -----
    // Clear background
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the chaotic trail
    if (sim.trail.length > 1) {
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      
      for (let i = 1; i < sim.trail.length; i++) {
        const pt0 = sim.trail[i - 1];
        const pt1 = sim.trail[i];
        
        ctx.beginPath();
        ctx.moveTo(pt0.x, pt0.y);
        ctx.lineTo(pt1.x, pt1.y);
        
        // Fade alpha based on age
        const alpha = Math.pow(i / sim.trail.length, 1.5);
        ctx.strokeStyle = `hsla(${pt1.hue}, 90%, 65%, ${alpha})`;
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    }

    // Draw lines (pendulum rods)
    ctx.beginPath();
    ctx.moveTo(sim.originX, sim.originY);
    ctx.lineTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = '#94a3b8'; // Slate 400
    ctx.lineWidth = 4;
    ctx.stroke();

    // Draw Origin Pivot
    ctx.beginPath();
    ctx.arc(sim.originX, sim.originY, 6, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // Helper for glowing masses
    const drawMass = (x, y, radius, color) => {
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.shadowBlur = 15;
      ctx.shadowColor = color;
      ctx.fill();
      ctx.shadowBlur = 0; // Reset
      
      // Inner core
      ctx.beginPath();
      ctx.arc(x, y, radius * 0.4, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.fill();
    };

    // Draw Masses
    const r1 = Math.min(Math.max(p.m1 * 0.6, 8), 24);
    const r2 = Math.min(Math.max(p.m2 * 0.6, 8), 24);
    
    // Highlight being dragged
    const color1 = sim.dragging === 1 ? '#22d3ee' : '#06b6d4'; // Cyan
    const color2 = sim.dragging === 2 ? '#f472b6' : '#ec4899'; // Pink

    drawMass(x1, y1, r1, color1);
    drawMass(x2, y2, r2, color2);

    // Loop
    requestRef.current = requestAnimationFrame(animate);
  }, []);

  // Initialize and handle window resizing
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      // Make internal canvas resolution match display size for crispness
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      
      const ctx = canvas.getContext('2d');
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;

      simRef.current.originX = rect.width / 2;
      simRef.current.originY = rect.height / 3;
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    requestRef.current = requestAnimationFrame(animate);
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(requestRef.current);
    };
  }, [animate]);

  // Pointer Interaction Logic (Mouse/Touch)
  const getPointerPos = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: clientX - rect.left,
      y: clientY - rect.top
    };
  };

  const handlePointerDown = (e) => {
    const pos = getPointerPos(e);
    const sim = simRef.current;
    const p = params;
    
    // Current positions of masses
    const x1 = sim.originX + p.l1 * Math.sin(sim.theta1);
    const y1 = sim.originY + p.l1 * Math.cos(sim.theta1);
    const x2 = x1 + p.l2 * Math.sin(sim.theta2);
    const y2 = y1 + p.l2 * Math.cos(sim.theta2);

    const hitRadius = 30; // Generous hit area for easy touch grabbing

    // Check hit on mass 2 first (it's on top logically)
    if (Math.hypot(pos.x - x2, pos.y - y2) < hitRadius) {
      sim.dragging = 2;
      sim.omega1 = 0;
      sim.omega2 = 0;
      sim.trail = [];
    } else if (Math.hypot(pos.x - x1, pos.y - y1) < hitRadius) {
      sim.dragging = 1;
      sim.omega1 = 0;
      sim.omega2 = 0;
      sim.trail = [];
    }
  };

  const handlePointerMove = (e) => {
    const sim = simRef.current;
    if (sim.dragging === 0) return;
    
    const pos = getPointerPos(e);
    const p = params;
    
    if (sim.dragging === 1) {
      // Calculate new angle for pendulum 1 relative to origin
      // Note: Math.atan2 takes (y, x). Since our vertical axis is 0 angle:
      // x = L * sin(t), y = L * cos(t) => tan(t) = x/y => t = atan2(x, y)
      sim.theta1 = Math.atan2(pos.x - sim.originX, pos.y - sim.originY);
      sim.omega1 = 0;
      sim.omega2 = 0;
    } else if (sim.dragging === 2) {
      // Need position of mass 1 to calculate angle for mass 2
      const x1 = sim.originX + p.l1 * Math.sin(sim.theta1);
      const y1 = sim.originY + p.l1 * Math.cos(sim.theta1);
      sim.theta2 = Math.atan2(pos.x - x1, pos.y - y1);
      sim.omega1 = 0;
      sim.omega2 = 0;
    }
  };

  const handlePointerUp = () => {
    simRef.current.dragging = 0;
  };

  // UI Handlers
  const handleReset = () => {
    simRef.current.theta1 = Math.PI / 2;
    simRef.current.theta2 = Math.PI / 2;
    simRef.current.omega1 = 0;
    simRef.current.omega2 = 0;
    simRef.current.trail = [];
  };

  const clearTrail = () => {
    simRef.current.trail = [];
  };

  const updateParam = (key, value) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) }));
    if (!isPlaying) {
       simRef.current.trail = []; // Clear trail on parameter change if paused
    }
  };

  return (
    <div className="flex flex-col md:flex-row h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden select-none">
      
      {/* Simulation Area */}
      <div 
        ref={containerRef}
        className="flex-1 relative touch-none shadow-[inset_0_0_100px_rgba(0,0,0,0.5)]"
      >
        <canvas
          ref={canvasRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onPointerLeave={handlePointerUp}
          className="absolute inset-0 block cursor-crosshair"
        />
        
        {/* On-canvas Title/Overlay */}
        <div className="absolute top-6 left-6 pointer-events-none">
          <h1 className="text-3xl font-bold tracking-tight text-white/90 drop-shadow-md flex items-center gap-3">
            <Activity className="w-8 h-8 text-cyan-400" />
            Chaotic Double Pendulum
          </h1>
          <p className="text-slate-400 mt-2 text-sm max-w-sm drop-shadow">
            Drag the glowing masses to set new initial conditions. Notice how minuscule changes drastically alter the trajectory.
          </p>
        </div>
      </div>

      {/* Control Panel */}
      <div className="w-full md:w-80 lg:w-96 bg-slate-900 border-l border-slate-800 p-6 flex flex-col gap-6 overflow-y-auto z-10 shadow-2xl">
        
        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium transition-all ${
              isPlaying 
                ? 'bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/30' 
                : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30'
            }`}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          
          <button 
            onClick={handleReset}
            className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <RotateCcw className="w-5 h-5" />
            Reset
          </button>
        </div>

        <button 
          onClick={clearTrail}
          className="w-full py-2 px-4 rounded-lg text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
        >
          Clear Trajectory Trail
        </button>

        <div className="h-px bg-slate-800 my-2"></div>

        {/* Physics Controls */}
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-2 text-slate-300 mb-2">
            <Settings className="w-5 h-5 text-slate-500" />
            <h2 className="font-semibold text-lg">System Parameters</h2>
          </div>

          <ControlSlider 
            label="Gravity" 
            value={params.g} min="0" max="5" step="0.1" 
            onChange={(v) => updateParam('g', v)} 
            color="text-slate-300"
          />
          
          <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 space-y-4">
            <h3 className="text-sm font-medium text-cyan-400 uppercase tracking-wider">Pendulum 1</h3>
            <ControlSlider 
              label="Length (L1)" 
              value={params.l1} min="50" max="250" step="5" 
              onChange={(v) => updateParam('l1', v)} 
            />
            <ControlSlider 
              label="Mass (M1)" 
              value={params.m1} min="2" max="40" step="1" 
              onChange={(v) => updateParam('m1', v)} 
            />
          </div>

          <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/50 space-y-4">
            <h3 className="text-sm font-medium text-pink-400 uppercase tracking-wider">Pendulum 2</h3>
            <ControlSlider 
              label="Length (L2)" 
              value={params.l2} min="50" max="250" step="5" 
              onChange={(v) => updateParam('l2', v)} 
            />
            <ControlSlider 
              label="Mass (M2)" 
              value={params.m2} min="2" max="40" step="1" 
              onChange={(v) => updateParam('m2', v)} 
            />
          </div>
        </div>

        <div className="mt-auto pt-6">
           <button 
              onClick={() => setShowInfo(!showInfo)}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors w-full justify-center"
           >
             <Info className="w-4 h-4" />
             {showInfo ? 'Hide Information' : 'How does this work?'}
           </button>
           
           {showInfo && (
             <div className="mt-4 text-xs text-slate-400 leading-relaxed bg-slate-950 p-4 rounded-lg border border-slate-800">
               <p className="mb-2">
                 This simulation numerically solves the non-linear Lagrangian equations of motion for a double pendulum using a semi-implicit Euler method.
               </p>
               <p>
                 Because the system is deeply chaotic, its future position is highly sensitive to initial conditions. Even grabbing a mass and shifting it by a fraction of a pixel will result in a completely different trajectory path over time.
               </p>
             </div>
           )}
        </div>

      </div>
    </div>
  );
}

// Reusable Slider Component
function ControlSlider({ label, value, min, max, step, onChange, color = "text-slate-300" }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center text-sm">
        <span className={`${color}`}>{label}</span>
        <span className="font-mono bg-slate-900 px-2 py-1 rounded text-slate-400 text-xs w-12 text-center border border-slate-700">
          {value}
        </span>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500 hover:accent-cyan-400 transition-all"
      />
    </div>
  );
}