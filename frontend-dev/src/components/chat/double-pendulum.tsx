import * as React from "react"

export function DoublePendulum() {
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null)
  
  // Physics parameters
  const [l1] = React.useState(90)
  const [l2] = React.useState(90)
  const [m1] = React.useState(10)
  const [m2] = React.useState(10)
  const [g] = React.useState(0.2) // gravity strength in simulator
  
  // Dynamic coordinates
  const stateRef = React.useRef({
    theta1: Math.PI / 2,
    theta2: Math.PI / 3,
    omega1: 0.0,
    omega2: 0.0,
    trail: [] as { x: number; y: number }[],
    isDragging: false,
    dragBob: null as 1 | 2 | null
  })

  React.useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationId: number

    const render = () => {
      const state = stateRef.current
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      
      const cx = canvas.width / 2
      const cy = 80

      // Physics Integration (Euler method for simplicity & real-time drag interaction)
      if (!state.isDragging) {
        const { theta1, theta2, omega1, omega2 } = state

        // Angular acceleration equations
        const num1 = -g * (2 * m1 + m2) * Math.sin(theta1) - m2 * g * Math.sin(theta1 - 2 * theta2) - 2 * Math.sin(theta1 - theta2) * m2 * (omega2 * omega2 * l2 + omega1 * omega1 * l1 * Math.cos(theta1 - theta2))
        const den1 = l1 * (2 * m1 + m2 - m2 * Math.cos(2 * theta1 - 2 * theta2))
        const alpha1 = num1 / den1

        const num2 = 2 * Math.sin(theta1 - theta2) * (omega1 * omega1 * l1 * (m1 + m2) + g * (m1 + m2) * Math.cos(theta1) + omega2 * omega2 * l2 * m2 * Math.cos(theta1 - theta2))
        const den2 = l2 * (2 * m1 + m2 - m2 * Math.cos(2 * theta1 - 2 * theta2))
        const alpha2 = num2 / den2

        state.omega1 += alpha1
        state.omega2 += alpha2
        state.theta1 += state.omega1
        state.theta2 += state.omega2

        // Friction/damping
        state.omega1 *= 0.999
        state.omega2 *= 0.999
      }

      // Positions
      const x1 = cx + l1 * Math.sin(state.theta1)
      const y1 = cy + l1 * Math.cos(state.theta1)

      const x2 = x1 + l2 * Math.sin(state.theta2)
      const y2 = y1 + l2 * Math.cos(state.theta2)

      // Add to trail
      if (!state.isDragging) {
        state.trail.push({ x: x2, y: y2 })
        if (state.trail.length > 100) {
          state.trail.shift()
        }
      }

      // Draw Trail
      ctx.beginPath()
      ctx.strokeStyle = "rgba(147, 51, 234, 0.45)"
      ctx.lineWidth = 1.5
      for (let i = 0; i < state.trail.length; i++) {
        const pt = state.trail[i]
        if (i === 0) ctx.moveTo(pt.x, pt.y)
        else ctx.lineTo(pt.x, pt.y)
      }
      ctx.stroke()

      // Draw rods
      ctx.beginPath()
      ctx.strokeStyle = "hsl(var(--muted-foreground) / 0.5)"
      ctx.lineWidth = 2.5
      ctx.moveTo(cx, cy)
      ctx.lineTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()

      // Draw pivot
      ctx.beginPath()
      ctx.arc(cx, cy, 4, 0, 2 * Math.PI)
      ctx.fillStyle = "hsl(var(--foreground))"
      ctx.fill()

      // Draw Bob 1
      ctx.beginPath()
      ctx.arc(x1, y1, 8, 0, 2 * Math.PI)
      ctx.fillStyle = "hsl(var(--primary))"
      ctx.fill()

      // Draw Bob 2
      ctx.beginPath()
      ctx.arc(x2, y2, 8, 0, 2 * Math.PI)
      ctx.fillStyle = "rgb(168, 85, 247)"
      ctx.fill()

      animationId = requestAnimationFrame(render)
    }

    render()

    return () => cancelAnimationFrame(animationId)
  }, [l1, l2, m1, m2, g])

  // Mouse Drag handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    const cx = canvas.width / 2
    const cy = 80

    const state = stateRef.current

    // Bob 1 position
    const x1 = cx + l1 * Math.sin(state.theta1)
    const y1 = cy + l1 * Math.cos(state.theta1)

    // Bob 2 position
    const x2 = x1 + l2 * Math.sin(state.theta2)
    const y2 = y1 + l2 * Math.cos(state.theta2)

    // Check hit bob 2
    const dist2 = Math.hypot(mouseX - x2, mouseY - y2)
    if (dist2 < 15) {
      state.isDragging = true
      state.dragBob = 2
      state.omega1 = 0
      state.omega2 = 0
      state.trail = []
      return
    }

    // Check hit bob 1
    const dist1 = Math.hypot(mouseX - x1, mouseY - y1)
    if (dist1 < 15) {
      state.isDragging = true
      state.dragBob = 1
      state.omega1 = 0
      state.omega2 = 0
      state.trail = []
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const state = stateRef.current
    if (!state.isDragging) return

    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    const cx = canvas.width / 2
    const cy = 80

    if (state.dragBob === 1) {
      const dx = mouseX - cx
      const dy = mouseY - cy
      state.theta1 = Math.atan2(dx, dy)
    } else if (state.dragBob === 2) {
      const x1 = cx + l1 * Math.sin(state.theta1)
      const y1 = cy + l1 * Math.cos(state.theta1)
      const dx = mouseX - x1
      const dy = mouseY - y1
      state.theta2 = Math.atan2(dx, dy)
    }
  }

  const handleMouseUp = () => {
    const state = stateRef.current
    state.isDragging = false
    state.dragBob = null
  }

  return (
    <div className="flex flex-col items-center gap-2 select-none">
      <canvas
        ref={canvasRef}
        width={400}
        height={320}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="border border-border/80 rounded-xl bg-card/60 shadow-inner cursor-pointer"
      />
      <div className="text-[10px] text-muted-foreground font-semibold">
        Drag either pendulum bob with your mouse to inject chaotic energy!
      </div>
    </div>
  )
}
