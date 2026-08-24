import Navbar from './components/aura/Navbar'
import Hero from './components/aura/Hero'
import MenuBarStrip from './components/aura/MenuBarStrip'
import InboxMockup from './components/aura/InboxMockup'
import FeatureTriage from './components/aura/FeatureTriage'
import LogoCloud from './components/aura/LogoCloud'
import Testimonials from './components/aura/Testimonials'
import Pricing from './components/aura/Pricing'
import FinalCTA from './components/aura/FinalCTA'

function App() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#0c0c0c] text-white">
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <filter id="c3-noise">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix
              type="matrix"
              values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.35 0"
            />
            <feComposite in2="SourceGraphic" operator="in" result="noise" />
            <feBlend in="SourceGraphic" in2="noise" mode="multiply" />
          </filter>
        </defs>
      </svg>

      <div className="fixed inset-0 z-0 pointer-events-none">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover pointer-events-none"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260508_064122_c4750c0e-7476-4b44-94a2-a85a65c63bf2.mp4"
        />
      </div>

      <div className="hidden md:block pointer-events-none fixed inset-y-0 left-1/2 -translate-x-[calc(50%+36rem)] w-px bg-white/10 z-[5]" />
      <div className="hidden md:block pointer-events-none fixed inset-y-0 left-1/2 translate-x-[calc(-50%+36rem)] w-px bg-white/10 z-[5]" />

      <div className="relative z-10">
        <Navbar />
        <Hero />
        <MenuBarStrip />
        <InboxMockup />
        <FeatureTriage />
        <LogoCloud />
        <Testimonials />
        <Pricing />
        <FinalCTA />
      </div>
    </div>
  )
}

export default App
