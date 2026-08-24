import { useState } from "react";
import { Check } from "lucide-react";
import "./Pricing.css";

type Plan = {
  tier: string;
  price: { monthly: string; yearly: string } | string;
  description: string;
  features: string[];
  pro?: boolean;
};

const plans: Plan[] = [
  {
    tier: "Free",
    price: "Free",
    description: "For creators taking their first steps with Forma.",
    features: [
      "Up to 3 projects in the cloud",
      "Image export up to 1080p",
      "Basic editing tools",
      "Free templates and icons",
      "Access via web and mobile app",
    ],
  },
  {
    tier: "Standard",
    price: { monthly: "$9,99/m", yearly: "$99,99/y" },
    description:
      "For freelancers and small teams who need more freedom and flexibility.",
    features: [
      "Up to 50 projects in the cloud",
      "Export up to 4K",
      "Advanced editing toolkit",
      "Team collaboration (up to 5 members)",
      "Access to premium template library",
    ],
  },
  {
    tier: "Pro",
    price: { monthly: "$19,99/m", yearly: "$199,99/y" },
    description:
      "For studios, agencies, and professional creators working with brands.",
    features: [
      "Unlimited projects",
      "Export up to 8K + animations",
      "AI-powered content generation tools",
      "Unlimited team members",
      "Brand customization",
    ],
    pro: true,
  },
];

export default function Pricing({ onOpenWaitlist }: { onOpenWaitlist: (plan: string) => void }) {
  const [yearly, setYearly] = useState(false);

  return (
    <section id="pricing" className="c3-pricing-section">
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <defs>
          <filter id="c3-noise">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.5"
              numOctaves={2}
              stitchTiles="stitch"
            />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.075" />
            </feComponentTransfer>
            <feComposite in2="SourceGraphic" operator="in" result="noise" />
            <feBlend in="SourceGraphic" in2="noise" mode="overlay" />
          </filter>
        </defs>
      </svg>

      <div className="c3-watermark-container">
        <div className="c3-watermark-main">
          <span className="c3-watermark-line-1">Your email.</span>
          <span className="c3-watermark-line-2">Revitalized</span>
        </div>
      </div>

      <div className="c3-grid">
        {plans.map((plan) => (
          <div
            key={plan.tier}
            className={plan.pro ? "c3-card c3-card-pro" : "c3-card"}
          >
            <div className="c3-tier-small">{plan.tier}</div>
            <div className="c3-tier-large">
              {typeof plan.price === "string"
                ? plan.price
                : yearly
                ? plan.price.yearly
                : plan.price.monthly}
            </div>
            <p className="c3-desc">{plan.description}</p>
            <ul className="c3-list">
              {plan.features.map((feature) => (
                <li key={feature}>
                  <span className="c3-check">
                    <Check size={14} color="#fff" />
                  </span>
                  {feature}
                </li>
              ))}
            </ul>
            <button className="c3-btn" onClick={() => onOpenWaitlist(plan.tier)}>
              Choose Plan
            </button>
          </div>
        ))}
      </div>

      <div className="c3-toggle-wrap">
        <span>Yearly</span>
        <button
          className={`c3-toggle ${yearly ? "active" : ""}`}
          onClick={() => setYearly((y) => !y)}
        >
          <span className="c3-toggle-knob" />
        </button>
      </div>
    </section>
  );
}
