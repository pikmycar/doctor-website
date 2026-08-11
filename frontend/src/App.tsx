import { lazy, Suspense, useEffect, useRef, useState, useCallback } from 'react'
import { AnimatePresence, motion, useMotionValue, useSpring } from 'framer-motion'
import { ArrowDownRight, ArrowUpRight, CalendarDays, Check, ChevronRight, Clock3, Menu, MoveRight, Phone, Quote, ShieldCheck, Sparkles, Stethoscope, X } from 'lucide-react'
const HeroScene = lazy(() => import('./HeroScene'))

const API_BASE = import.meta.env.VITE_BACKEND_URL || ''

const services = [
  { number: '01', title: 'Preventive care', body: 'A clear, considered plan for your health today — and the decades ahead.', icon: ShieldCheck, tone: 'clay' },
  { number: '02', title: 'Precision medicine', body: 'Thoughtful diagnostics and treatment, shaped around your body and your life.', icon: Sparkles, tone: 'sky' },
  { number: '03', title: 'Ongoing partnership', body: 'A trusted clinical relationship that makes every next step feel lighter.', icon: CalendarDays, tone: 'forest' },
]

const credentials = [
  'MD, Yale School of Medicine',
  'Board Certified · Internal Medicine',
  'Fellow, American College of Physicians',
  'Faculty, NYU Langone',
]

const testimonials = [
  { quote: 'I finally have a doctor who listens before she recommends. I leave every visit with a plan I actually understand.', name: 'Amelia R.', context: 'Patient · 3 years' },
  { quote: 'The unhurried care Meridian offers is a genuine luxury in modern medicine. It changed how I think about my health.', name: 'Julian K.', context: 'Patient · since 2023' },
  { quote: 'Warm, precise, and quietly world-class. My family trusts Meridian with everything, from routine checkups to hard conversations.', name: 'Priya S.', context: 'Family patient' },
]

type Slot = { id: string; start: string; end: string; label: string; available: boolean }
type DaySlots = { date: string; weekday: string; day_label: string; slots: Slot[] }

function AppointmentDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [days, setDays] = useState<DaySlots[]>([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [activeDayIdx, setActiveDayIdx] = useState(0)
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [website, setWebsite] = useState('') // honeypot
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [confirmedLabel, setConfirmedLabel] = useState('')
  const firstInput = useRef<HTMLInputElement>(null)
  const previousActive = useRef<HTMLElement | null>(null)

  const loadAvailability = useCallback(async () => {
    setLoadingSlots(true)
    try {
      const res = await fetch(`${API_BASE}/api/availability`)
      if (!res.ok) throw new Error('availability failed')
      const data: DaySlots[] = await res.json()
      setDays(data)
      setActiveDayIdx(0)
    } catch {
      setErrorMsg('We could not load times. Please try again in a moment.')
    } finally {
      setLoadingSlots(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    previousActive.current = document.activeElement as HTMLElement
    setSubmitted(false)
    setSelectedSlot(null)
    setErrorMsg('')
    setName(''); setEmail(''); setMessage(''); setWebsite('')
    loadAvailability()
    setTimeout(() => firstInput.current?.focus(), 40)
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
  }, [open, onClose, loadAvailability])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!selectedSlot) { setErrorMsg('Please pick a time that works for you.'); return }
    setSubmitting(true); setErrorMsg('')
    try {
      const res = await fetch(`${API_BASE}/api/appointments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, message, slot_start: selectedSlot.start, website }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: 'Something went wrong.' }))
        throw new Error(detail.detail || 'Something went wrong.')
      }
      const day = days[activeDayIdx]
      setConfirmedLabel(`${day.day_label} · ${selectedSlot.label}`)
      setSubmitted(true)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Something went wrong.')
      loadAvailability()
    } finally {
      setSubmitting(false)
    }
  }

  const activeDay = days[activeDayIdx]

  return <AnimatePresence>{open && <motion.div className="dialog-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={onClose}>
    <motion.div className="dialog dialog-wide" role="dialog" aria-modal="true" aria-labelledby="appointment-title" initial={{ opacity: 0, y: 24, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 16 }} onMouseDown={(event) => event.stopPropagation()}>
      <button className="icon-button dialog-close" onClick={onClose} aria-label="Close appointment dialog" data-testid="appointment-dialog-close"><X size={18} /></button>
      {!submitted ? <>
        <span className="eyebrow">Start a conversation</span>
        <h2 id="appointment-title">Make room for your health.</h2>
        <p className="dialog-copy">Pick a time that suits you. Our care coordinator will confirm within one working day.</p>

        <div className="slot-picker" data-testid="slot-picker">
          <div className="day-tabs" role="tablist" aria-label="Available days">
            {days.map((day, idx) => (
              <button
                key={day.date}
                type="button"
                role="tab"
                aria-selected={idx === activeDayIdx}
                className={`day-tab ${idx === activeDayIdx ? 'active' : ''}`}
                onClick={() => setActiveDayIdx(idx)}
                data-testid={`day-tab-${idx}`}
              >
                <span className="day-tab-wd">{day.weekday}</span>
                <span className="day-tab-num">{day.day_label.split(' ')[1]}</span>
              </button>
            ))}
            {loadingSlots && days.length === 0 && (
              <div className="slot-loading">Loading times…</div>
            )}
          </div>
          <div className="slot-grid" role="tabpanel">
            {activeDay?.slots.map((slot) => (
              <button
                key={slot.id}
                type="button"
                className={`slot-chip ${!slot.available ? 'is-booked' : ''} ${selectedSlot?.id === slot.id ? 'is-selected' : ''}`}
                disabled={!slot.available}
                onClick={() => { setSelectedSlot(slot); setErrorMsg('') }}
                data-testid={`slot-${slot.id}`}
                aria-pressed={selectedSlot?.id === slot.id}
              >
                {slot.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={submit}>
          <label>Name<input ref={firstInput} required value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" data-testid="appointment-name-input" /></label>
          <label>Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" data-testid="appointment-email-input" /></label>
          <label>What brings you in?<textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="A little context helps us prepare" data-testid="appointment-message-input" /></label>
          {/* Honeypot: real users leave this blank; bots fill it. Hidden from screen readers + tab order. */}
          <div className="hp-field" aria-hidden="true">
            <label>Your website<input type="text" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} data-testid="appointment-hp-input" /></label>
          </div>
          {errorMsg && <p className="dialog-error" role="alert" data-testid="appointment-error">{errorMsg}</p>}
          <button className="button button-dark full" type="submit" disabled={submitting || !selectedSlot} data-testid="appointment-submit-button">
            {submitting ? 'Sending…' : selectedSlot ? `Request · ${activeDay?.day_label} ${selectedSlot.label}` : 'Pick a time to continue'}
            <ArrowUpRight size={17} />
          </button>
        </form>
      </> : <div className="success-state" data-testid="appointment-confirmation">
        <div className="success-icon"><Check size={22} /></div>
        <span className="eyebrow">Request received</span>
        <h2>We'll be in touch.</h2>
        <p>You're pencilled in for <strong>{confirmedLabel}</strong>. A care coordinator will confirm the details shortly.</p>
        <button className="button button-dark full" onClick={onClose} data-testid="appointment-confirmation-close">Done</button>
      </div>}
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
      <nav className={menuOpen ? 'main-nav open' : 'main-nav'} data-testid="main-navigation">
        <a href="#about" data-testid="nav-about-link">About</a>
        <a href="#doctor" data-testid="nav-doctor-link">Your doctor</a>
        <a href="#expertise" data-testid="nav-expertise-link">Expertise</a>
        <a href="#stories" data-testid="nav-stories-link">Stories</a>
        <a href="#contact" data-testid="nav-contact-link">Contact</a>
        <button className="button button-small" onClick={() => setDialogOpen(true)} data-testid="header-book-button">Book an appointment <ArrowUpRight size={15} /></button>
      </nav>
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

      <section className="intro-section section-pad" id="about"><div className="section-kicker"><span className="eyebrow">A different kind of doctor's office</span><span className="rule" /></div><div className="intro-grid"><h2 data-testid="about-heading">The best care starts with <em>being heard.</em></h2><div><p className="large-copy" data-testid="about-description">Healthcare can feel complicated. Your care shouldn't. We pair rigorous clinical thinking with the kind of attention that makes you feel like a person, not a chart.</p><a href="#doctor" className="text-link" data-testid="about-approach-link">Meet your doctor <MoveRight size={16} /></a></div></div></section>

      <section className="doctor-section section-pad" id="doctor" data-testid="doctor-section">
        <div className="doctor-grid">
          <motion.div
            className="doctor-portrait"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: .8 }}
            style={{ x: smoothX, y: smoothY }}
          >
            <img
              src="https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=900&q=80"
              alt="Dr. Elena Marchetti, founding physician of Meridian Medical Studio"
              loading="lazy"
              data-testid="doctor-portrait-image"
            />
            <div className="doctor-badge" aria-hidden="true">
              <Stethoscope size={16} />
              <span>Meridian · Est. 2015</span>
            </div>
          </motion.div>
          <div className="doctor-copy">
            <span className="eyebrow">Your doctor</span>
            <h2 data-testid="doctor-heading">Dr. Elena Marchetti,<br /><em>internist &amp; founder.</em></h2>
            <p className="large-copy" data-testid="doctor-bio">
              I trained in the busiest hospital in the country and built Meridian because I wanted the opposite of what I saw there — enough time, real conversation, and medicine tailored to your life.
            </p>
            <p className="doctor-philosophy" data-testid="doctor-philosophy">
              My philosophy is quiet and simple: treat the person before the problem, use evidence like a compass rather than a wall, and never rush a first appointment.
            </p>
            <ul className="doctor-credentials" data-testid="doctor-credentials">
              {credentials.map((c) => (
                <li key={c}><span className="cred-dot" />{c}</li>
              ))}
            </ul>
            <button className="button button-dark" onClick={() => setDialogOpen(true)} data-testid="doctor-book-button">
              Book a first visit <ArrowUpRight size={17} />
            </button>
          </div>
        </div>
      </section>

      <section className="services-section section-pad" id="expertise"><div className="services-intro"><span className="eyebrow">What we do</span><h2>Deep expertise.<br /><em>Clear direction.</em></h2><p>From prevention to complex questions, we create a considered path forward.</p></div><div className="service-list">{services.map((service, index) => { const Icon = service.icon; return <motion.article className={`service-card ${service.tone}`} key={service.number} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-80px' }} transition={{ delay: index * .1 }} whileHover={{ y: -8, rotateX: 2, rotateY: index % 2 ? -2 : 2 }} data-testid={`service-card-${service.number}`}><div className="service-top"><span className="service-number">{service.number}</span><Icon size={24} strokeWidth={1.5} /></div><h3>{service.title}</h3><p>{service.body}</p><div className="card-arrow"><ChevronRight size={18} /></div></motion.article> })}</div></section>

      <section className="stories-section section-pad" id="stories" data-testid="stories-section">
        <div className="stories-header">
          <span className="eyebrow">Patient stories</span>
          <h2>Care, in their <em>own words.</em></h2>
          <p>A few notes from patients who let us into their lives.</p>
        </div>
        <div className="stories-grid">
          {testimonials.map((t, i) => (
            <motion.figure
              key={t.name}
              className="story-card"
              initial={{ opacity: 0, y: 40, rotateX: -8 }}
              whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ delay: i * 0.12, duration: 0.7 }}
              whileHover={{ y: -6, rotateX: 2, rotateY: i % 2 ? -2 : 2 }}
              data-testid={`story-card-${i}`}
            >
              <Quote size={28} strokeWidth={1.2} className="story-mark" aria-hidden="true" />
              <blockquote>{t.quote}</blockquote>
              <figcaption>
                <strong>{t.name}</strong>
                <span>{t.context}</span>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </section>

      <section className="approach-section section-pad" id="approach"><div className="approach-card"><div className="approach-copy"><span className="eyebrow">Our approach</span><h2>More time.<br /><em>Better questions.</em></h2><p>Every appointment is unrushed by design. We listen for the detail that changes everything, then translate it into a plan you can actually live with.</p><button className="button button-light" onClick={() => setDialogOpen(true)} data-testid="approach-book-button">Meet your care team <ArrowUpRight size={17} /></button></div><div className="approach-stats"><div><span>01</span><strong>Listen<br />closely</strong></div><div><span>02</span><strong>Think<br />deeply</strong></div><div><span>03</span><strong>Care<br />always</strong></div></div></div></section>
      <section className="contact-strip section-pad" id="contact"><div><span className="eyebrow">Ready when you are</span><h2>Let's make a little<br /><em>more room.</em></h2></div><div className="contact-details"><a href="tel:+12125550148" data-testid="phone-contact-link"><Phone size={18} /> +1 212 555 0148</a><span><Clock3 size={18} /> Mon–Fri · 9am–5pm</span><button className="button button-dark" onClick={() => setDialogOpen(true)} data-testid="contact-book-button">Book an appointment <ArrowUpRight size={17} /></button></div></section>
    </main>
    <footer className="site-footer"><a className="brand brand-light" href="#top" data-testid="footer-brand-link"><span className="brand-mark">M</span><span>Meridian<br /><i>medical studio</i></span></a><p>Thoughtful medicine for modern lives.</p><span className="footer-note">© 2026 Meridian Medical Studio</span></footer>
    <AppointmentDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
  </div>
}
