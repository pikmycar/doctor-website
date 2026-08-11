import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useMotionValue, useSpring } from 'framer-motion'
import { ArrowDownRight, ArrowUpRight, CalendarDays, Check, ChevronRight, Clock3, Menu, MoveRight, Phone, ShieldCheck, Sparkles, X } from 'lucide-react'
const HeroScene = lazy(() => import('./HeroScene'))

const services = [
  { number: '01', title: 'Preventive care', body: 'A clear, considered plan for your health today — and the decades ahead.', icon: ShieldCheck, tone: 'clay' },
  { number: '02', title: 'Precision medicine', body: 'Thoughtful diagnostics and treatment, shaped around your body and your life.', icon: Sparkles, tone: 'sky' },
  { number: '03', title: 'Ongoing partnership', body: 'A trusted clinical relationship that makes every next step feel lighter.', icon: CalendarDays, tone: 'forest' },
]

function AppointmentDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [submitted, setSubmitted] = useState(false)
  const firstInput = useRef<HTMLInputElement>(null)
  const previousActive = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (!open) return
    previousActive.current = document.activeElement as HTMLElement
    firstInput.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab') return
      const dialog = document.querySelector<HTMLElement>('[role="dialog"]')
      if (!dialog) return
      const focusable = [...dialog.querySelectorAll<HTMLElement>('button, input, textarea')].filter((element) => !element.hasAttribute('disabled'))
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => { document.removeEventListener('keydown', closeOnEscape); previousActive.current?.focus() }
  }, [open, onClose])
  return <AnimatePresence>{open && <motion.div className="dialog-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={onClose}>
    <motion.div className="dialog" role="dialog" aria-modal="true" aria-labelledby="appointment-title" initial={{ opacity: 0, y: 24, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 16 }} onMouseDown={(event) => event.stopPropagation()}>
      <button className="icon-button dialog-close" onClick={onClose} aria-label="Close appointment dialog" data-testid="appointment-dialog-close"><X size={18} /></button>
      {!submitted ? <>
        <span className="eyebrow">Start a conversation</span><h2 id="appointment-title">Make room for your health.</h2>
        <p className="dialog-copy">Leave a few details and our care coordinator will be in touch within one working day.</p>
        <form onSubmit={(event) => { event.preventDefault(); setSubmitted(true) }}>
          <label>Name<input ref={firstInput} required placeholder="Your name" data-testid="appointment-name-input" /></label>
          <label>Email<input required type="email" placeholder="you@example.com" data-testid="appointment-email-input" /></label>
          <label>What brings you in?<textarea rows={3} placeholder="A little context helps us prepare" data-testid="appointment-message-input" /></label>
          <button className="button button-dark full" type="submit" data-testid="appointment-submit-button">Request an appointment <ArrowUpRight size={17} /></button>
        </form>
      </> : <div className="success-state" data-testid="appointment-confirmation"><div className="success-icon"><Check size={22} /></div><span className="eyebrow">Request received</span><h2>We’ll be in touch.</h2><p>Thank you for trusting us with your next step. A care coordinator will reach out shortly.</p><button className="button button-dark full" onClick={onClose} data-testid="appointment-confirmation-close">Done</button></div>}
    </motion.div>
  </motion.div>}</AnimatePresence>
}

export default function App() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const pointerX = useMotionValue(0)
  const pointerY = useMotionValue(0)
  const smoothX = useSpring(pointerX, { stiffness: 80, damping: 20 })
  const smoothY = useSpring(pointerY, { stiffness: 80, damping: 20 })
  const handlePointer = (event: React.PointerEvent<HTMLElement>) => { pointerX.set((event.clientX / window.innerWidth - .5) * 16); pointerY.set((event.clientY / window.innerHeight - .5) * 10) }

  return <div className="site-shell" onPointerMove={handlePointer}>
    <header className="site-header" data-testid="site-header"><a className="brand" href="#top" data-testid="brand-link"><span className="brand-mark">M</span><span>Meridian<br /><i>medical studio</i></span></a>
      <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation" data-testid="mobile-menu-button">{menuOpen ? <X size={20} /> : <Menu size={20} />}</button>
      <nav className={menuOpen ? 'main-nav open' : 'main-nav'} data-testid="main-navigation"><a href="#about" data-testid="nav-about-link">About</a><a href="#expertise" data-testid="nav-expertise-link">Expertise</a><a href="#approach" data-testid="nav-approach-link">Approach</a><a href="#contact" data-testid="nav-contact-link">Contact</a><button className="button button-small" onClick={() => setDialogOpen(true)} data-testid="header-book-button">Book an appointment <ArrowUpRight size={15} /></button></nav>
    </header>

    <main id="top">
      <section className="hero-section section-pad"><div className="hero-grid">
        <motion.div className="hero-copy" initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7 }}>
          <span className="eyebrow" data-testid="hero-eyebrow">Private practice · New York / Remote</span>
          <h1 data-testid="hero-heading">Medicine, made <em>human.</em></h1>
          <p className="hero-text" data-testid="hero-description">A calmer, more considered way to care for your whole self. Expert medicine, without the noise.</p>
          <div className="hero-actions"><button className="button button-dark" onClick={() => setDialogOpen(true)} data-testid="hero-book-button">Find your next step <ArrowUpRight size={17} /></button><a className="text-link" href="#expertise" data-testid="hero-explore-link">Explore our approach <MoveRight size={16} /></a></div>
          <div className="hero-meta"><span><strong>24+</strong> years of care</span><span><strong>4.9</strong> patient rating</span></div>
        </motion.div>
        <motion.div className="hero-visual" style={{ x: smoothX, y: smoothY }} initial={{ opacity: 0, scale: .92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1, delay: .15 }}>
          <div className="orb-glow" aria-hidden="true" /><div className="annotation annotation-top"><span>01 / your health</span><i /></div><div className="annotation annotation-bottom"><i /><span>in focus</span></div>
          <div className="canvas-wrap" data-testid="hero-3d-object" aria-label="Interactive translucent medical orb representing whole-person care"><Suspense fallback={<div className="orb-fallback" aria-hidden="true" />}><HeroScene /></Suspense></div>
          <div className="credential-card" data-testid="hero-credential-card"><span className="credential-dot" /><span>Board certified<br /><strong>Internal medicine</strong></span><ArrowDownRight size={18} /></div>
        </motion.div>
      </div><a href="#expertise" className="scroll-cue" data-testid="scroll-cue"><span>Scroll to explore</span><ArrowDownRight size={16} /></a></section>

      <section className="intro-section section-pad" id="about"><div className="section-kicker"><span className="eyebrow">A different kind of doctor’s office</span><span className="rule" /></div><div className="intro-grid"><h2 data-testid="about-heading">The best care starts with <em>being heard.</em></h2><div><p className="large-copy" data-testid="about-description">Healthcare can feel complicated. Your care shouldn’t. We pair rigorous clinical thinking with the kind of attention that makes you feel like a person, not a chart.</p><a href="#approach" className="text-link" data-testid="about-approach-link">Why Meridian <MoveRight size={16} /></a></div></div></section>

      <section className="services-section section-pad" id="expertise"><div className="services-intro"><span className="eyebrow">What we do</span><h2>Deep expertise.<br /><em>Clear direction.</em></h2><p>From prevention to complex questions, we create a considered path forward.</p></div><div className="service-list">{services.map((service, index) => { const Icon = service.icon; return <motion.article className={`service-card ${service.tone}`} key={service.number} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-80px' }} transition={{ delay: index * .1 }} whileHover={{ y: -8, rotateX: 2, rotateY: index % 2 ? -2 : 2 }} data-testid={`service-card-${service.number}`}><div className="service-top"><span className="service-number">{service.number}</span><Icon size={24} strokeWidth={1.5} /></div><h3>{service.title}</h3><p>{service.body}</p><div className="card-arrow"><ChevronRight size={18} /></div></motion.article> })}</div></section>

      <section className="approach-section section-pad" id="approach"><div className="approach-card"><div className="approach-copy"><span className="eyebrow">Our approach</span><h2>More time.<br /><em>Better questions.</em></h2><p>Every appointment is unrushed by design. We listen for the detail that changes everything, then translate it into a plan you can actually live with.</p><button className="button button-light" onClick={() => setDialogOpen(true)} data-testid="approach-book-button">Meet your care team <ArrowUpRight size={17} /></button></div><div className="approach-stats"><div><span>01</span><strong>Listen<br />closely</strong></div><div><span>02</span><strong>Think<br />deeply</strong></div><div><span>03</span><strong>Care<br />always</strong></div></div></div></section>
      <section className="contact-strip section-pad" id="contact"><div><span className="eyebrow">Ready when you are</span><h2>Let’s make a little<br /><em>more room.</em></h2></div><div className="contact-details"><a href="tel:+12125550148" data-testid="phone-contact-link"><Phone size={18} /> +1 212 555 0148</a><span><Clock3 size={18} /> Mon–Fri · 9am–5pm</span><button className="button button-dark" onClick={() => setDialogOpen(true)} data-testid="contact-book-button">Book an appointment <ArrowUpRight size={17} /></button></div></section>
    </main>
    <footer className="site-footer"><a className="brand brand-light" href="#top" data-testid="footer-brand-link"><span className="brand-mark">M</span><span>Meridian<br /><i>medical studio</i></span></a><p>Thoughtful medicine for modern lives.</p><span className="footer-note">© 2026 Meridian Medical Studio</span></footer>
    <AppointmentDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
  </div>
}