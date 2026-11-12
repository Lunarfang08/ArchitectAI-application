"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef } from "react";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import styles from "./landing-page.module.css";
import { ArchitectLogo } from "./architect-logo";
import { ProductDemo } from "./product-demo";

const capabilities = [
  { eyebrow: "DESIGN", title: "Architecture with context.", copy: "Turn requirements and your own technical knowledge into a clear system blueprint.", className: styles.cardWide },
  { eyebrow: "MAKE", title: "From intent to repository.", copy: "Generate a complete, reviewable file manifest. Nothing touches disk until you say so.", className: styles.cardTall },
  { eyebrow: "REVIEW", title: "Find risks before release.", copy: "Inspect proposed code and tests without running untrusted files.", className: styles.cardSmall },
  { eyebrow: "OWN", title: "Local first. Cloud optional.", copy: "Use a local model and local project storage by default. Enable cloud connections only when needed.", className: styles.cardSmall },
];

const workflow = [
  ["Requirement", "Describe the system in natural language."],
  ["Project context", "Ground the design in local documents."],
  ["Architecture", "Shape the system around your requirements."],
  ["Generation", "Preview every proposed project file."],
  ["Review", "Inspect findings and approve test files."],
];

function ArrowIcon() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export function LandingPage() {
  const shellRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const root = shellRef.current;
    if (!root) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let cleanup = () => {};
    function setup() {
      cleanup();
      if (!root) return;
      if (preference.matches) {
        root.removeAttribute("data-motion");
        return;
      }
      const lenis = new Lenis({ lerp: 0.085, autoRaf: true, anchors: { offset: -90 } });
      root.dataset.motion = "true";
      const sequence = root.querySelector<HTMLElement>("[data-sequence]");
      const manifesto = root.querySelector<HTMLElement>("#method");
      let frame = 0;
      const clamp = (value: number) => Math.min(1, Math.max(0, value));
      const update = () => {
        frame = 0;
        const height = window.innerHeight;
        root.style.setProperty("--page-progress", String(window.scrollY / Math.max(1, document.documentElement.scrollHeight - height)));
        root.style.setProperty("--hero-scroll", String(clamp(window.scrollY / height)));
        root.dataset.scrolled = String(window.scrollY > 60);
        if (sequence) {
          const progress = clamp(-sequence.getBoundingClientRect().top / Math.max(1, sequence.offsetHeight - height));
          sequence.style.setProperty("--sequence-progress", String(progress));
          sequence.dataset.stage = String(Math.min(4, Math.floor(progress * 5)));
        }
        if (manifesto) {
          const progress = clamp((height * .8 - manifesto.getBoundingClientRect().top) / (height * .65));
          manifesto.style.setProperty("--reading", `${progress * 100}%`);
        }
      };
      const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
      window.addEventListener("scroll", schedule, { passive: true });
      window.addEventListener("resize", schedule);
      update();
      cleanup = () => {
        lenis.destroy();
        window.removeEventListener("scroll", schedule);
        window.removeEventListener("resize", schedule);
        cancelAnimationFrame(frame);
      };
    }
    setup();
    preference.addEventListener("change", setup);
    return () => { cleanup(); preference.removeEventListener("change", setup); };
  }, []);

  useEffect(() => {
    const root = shellRef.current;
    if (!root) return;
    const revealItems = root.querySelectorAll<HTMLElement>("[data-reveal]");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      revealItems.forEach((item) => item.dataset.visible = "true");
      return;
    }
    if (!("IntersectionObserver" in window)) {
      revealItems.forEach((item) => item.dataset.visible = "true");
      return;
    }
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) {
        (entry.target as HTMLElement).dataset.visible = "true";
        observer.unobserve(entry.target);
      }
    }), { threshold: 0.14 });
    revealItems.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  function trackPointer(event: React.PointerEvent<HTMLElement>) {
    if (event.pointerType === "touch" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--mx", ((event.clientX - bounds.left) / bounds.width - 0.5).toFixed(3));
    event.currentTarget.style.setProperty("--my", ((event.clientY - bounds.top) / bounds.height - 0.5).toFixed(3));
  }

  return (
      <main className={styles.shell} ref={shellRef} onPointerMove={trackPointer}>
        <a href="#method" className={styles.skipLink}>Skip introduction</a>
        <div className={styles.scrollProgress} aria-hidden="true" />
        <nav className={styles.nav} aria-label="Primary navigation">
          <Link className={styles.wordmark} href="/" aria-label="ArchitectAI home"><ArchitectLogo className={styles.mark} /><span>ArchitectAI</span></Link>
          <div className={styles.navLinks}><a href="#method">Overview</a><a href="#capabilities">Capabilities</a><a href="#workflow">How it works</a></div>
          <Link className={styles.navCta} href="/workspace">Enter workspace <ArrowIcon /></Link>
        </nav>

        <section className={styles.hero}>
          <div className={styles.heroArt} aria-hidden="true"><Image src="/architect-ai-hero.png" alt="" fill priority sizes="100vw" className={styles.heroImage} /></div>
          <div className={styles.heroNoise} aria-hidden="true" /><div className={styles.orbit} aria-hidden="true"><span /></div>
          <div className={styles.heroCopy}>
            <p className={styles.kicker} data-reveal><span className={styles.statusLight} /> SOFTWARE ARCHITECTURE WORKSPACE</p>
            <h1 data-reveal>Don&apos;t just prompt.<span>Architect.</span></h1>
            <p className={styles.heroLead} data-reveal>Turn requirements into a considered system design, then review proposed code before it reaches your project.</p>
            <div className={styles.heroActions} data-reveal><Link className={styles.primaryCta} href="/workspace">Start architecting <ArrowIcon /></Link><a className={styles.textCta} href="#method">See how it thinks <span>↓</span></a></div>
          </div>
          <div className={styles.heroCoordinates} aria-hidden="true"><span>SOFTWARE / SYSTEM DESIGN</span><b>Ideas, given structure.</b><span>DESIGNED TO WORK WITH YOU ↗</span></div>
          <div className={styles.heroFoot}><span>DESIGN BEFORE IMPLEMENTATION</span><span className={styles.scrollCue}>EXPLORE <i /></span></div>
        </section>

        <section className={styles.signalBar} aria-label="Workspace features"><span>LOCAL BY DEFAULT</span><i /><span>PROJECT CONTEXT</span><i /><span>REVIEWABLE FILES</span><i /><span>HUMAN APPROVAL</span></section>

        <section className={styles.manifesto} id="method">
          <div className={styles.sectionIndex} data-reveal><p>OVERVIEW</p></div>
          <div className={styles.manifestoBody}>
            <p className={styles.manifestoLead} data-reveal>Great software begins<br />before the first line.<em>Give your ideas a place to become extraordinary.</em></p>
            <div className={styles.manifestoGrid}><p data-reveal>A thought becomes a brief. A brief becomes a blueprint. Your documents and constraints inform the design.</p><p data-reveal>Explore options. Inspect the architecture. Review the code. Decide exactly what makes it into your project.</p></div>
          </div>
        </section>

        <section className={styles.capabilities} id="capabilities">
          <div className={styles.sectionHeading} data-reveal><div><p>CAPABILITIES</p></div><h2>A clearer path<br />from idea to system.</h2></div>
          <div className={styles.cardGrid}>{capabilities.map((item) => <article className={`${styles.capabilityCard} ${item.className}`} key={item.title} data-reveal><div className={styles.cardTop}><span>{item.eyebrow}</span><i /></div><div className={styles.cardDiagram} aria-hidden="true"><i /><i /><i /><i /><span>{item.eyebrow}</span></div><div><p>{item.eyebrow}</p><h3>{item.title}</h3><div className={styles.cardCopy}>{item.copy}</div></div></article>)}</div>
        </section>

        <section className={styles.sequence} id="workflow" data-sequence data-stage="0">
          <div className={styles.sequenceSticky}>
            <div className={styles.sequenceHeading}><p className={styles.kicker}>FROM REQUIREMENT TO REVIEW</p><h2>See the work<br /><em>take shape.</em></h2><p>Move from an initial brief<br />to a reviewed design.</p></div>
            <div className={styles.blueprint} aria-hidden="true">
              <div className={styles.blueprintLabel}><span>ARCHITECTURE STUDY</span><span>SCROLL TO EXPLORE ↓</span></div>
              <div className={styles.assembly}>
                {workflow.map(([title], index) => <div key={title} className={styles.blueprintLayer} data-layer={index}><b>{title}</b><i /></div>)}
              </div>
              <div className={styles.blueprintAxis}><span>X — INTENT</span><span>Y — POSSIBILITY</span><span>Z — STRUCTURE</span></div>
            </div>
            <div className={styles.sequenceSteps}>{workflow.map(([title, copy], index) => <article key={title} data-step={index}><h3>{title}</h3><p>{copy}</p></article>)}</div>
            <div className={styles.sequenceTrack} aria-hidden="true"><i /></div>
          </div>
        </section>

        <ProductDemo />
        <section className={styles.localSection}>
          <div className={styles.localVisual} data-reveal><div className={styles.core}><span>LOCAL</span><i /><b>PRIVATE BY DEFAULT</b></div><div className={styles.ringOne} /><div className={styles.ringTwo} /></div>
          <div className={styles.localCopy} data-reveal><p className={styles.kicker}>BUILT FOR LOCAL WORK</p><h2>Your architecture.<br /><em>Your machine.</em></h2><p>Your model, documents, and project files stay on your machine by default. Optional cloud connections remain off until you enable them.</p><ul><li><span>01</span> Local model execution</li><li><span>02</span> Review before file writes</li><li><span>03</span> Generated code is never run</li></ul></div>
        </section>

        <section className={styles.finalCta}><div className={styles.ctaGlow} aria-hidden="true" /><p className={styles.kicker} data-reveal>YOUR NEXT SYSTEM STARTS HERE</p><h2 data-reveal>Turn the idea in your head<br />into architecture you can trust.</h2><Link className={styles.primaryCta} href="/workspace" data-reveal>Open ArchitectAI <ArrowIcon /></Link></section>

        <footer className={styles.footer}><Link className={styles.wordmark} href="/"><ArchitectLogo className={styles.mark} /><span>ArchitectAI</span></Link><p>Software architecture, made clearer.</p><span>© 2026</span></footer>
      </main>
  );
}
