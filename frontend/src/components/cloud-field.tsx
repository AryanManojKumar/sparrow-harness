/**
 * The cloud layer behind the console.
 *
 * SVG fractal noise rather than CSS gradients: radial-gradients can only
 * make soft ellipses, which read as vignettes, not weather. `feTurbulence`
 * with a few octaves gives genuine wispy structure, and the whole thing is
 * generated in the browser — no image asset, no network request.
 *
 * Rendered into a small viewBox and stretched with `preserveAspectRatio
 * ="none"`: the filter runs over a few hundred user units instead of a few
 * million device pixels, which keeps it cheap, and the upscale softens the
 * noise for free.
 */
export function CloudField() {
  return (
    <div className="console-clouds" aria-hidden="true">
      <svg
        viewBox="0 0 600 400"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
        className="size-full"
      >
        <defs>
          {/* Far layer — broad, dim, low frequency. */}
          <filter id="cloud-far" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.009"
              numOctaves="4"
              seed="11"
              result="noise"
            />
            <feColorMatrix
              in="noise"
              type="matrix"
              values="0 0 0 0 0.62
                      0 0 0 0 0.68
                      0 0 0 0 0.85
                      0.9 0 0 0 -0.36"
            />
            <feGaussianBlur stdDeviation="3" />
          </filter>

          {/* Near layer — tighter, brighter, offset seed so the two don't
              trace the same shapes. */}
          <filter id="cloud-near" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.018"
              numOctaves="5"
              seed="29"
              result="noise"
            />
            <feColorMatrix
              in="noise"
              type="matrix"
              values="0 0 0 0 0.70
                      0 0 0 0 0.74
                      0 0 0 0 0.92
                      0.8 0 0 0 -0.42"
            />
            <feGaussianBlur stdDeviation="1.5" />
          </filter>

          {/* Clouds gather at the top and thin out toward the prompt box, so
              the content sits on quiet ground. */}
          <linearGradient id="cloud-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="white" stopOpacity="0.95" />
            <stop offset="45%" stopColor="white" stopOpacity="0.45" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </linearGradient>
          <mask id="cloud-mask">
            <rect width="600" height="400" fill="url(#cloud-fade)" />
          </mask>
        </defs>

        <g mask="url(#cloud-mask)">
          <rect width="600" height="400" filter="url(#cloud-far)" opacity="0.55" />
          <rect width="600" height="400" filter="url(#cloud-near)" opacity="0.32" />
        </g>
      </svg>
    </div>
  );
}
