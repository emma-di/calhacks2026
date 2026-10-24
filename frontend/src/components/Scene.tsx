export default function Scene() {
  return (
    <svg
      className="scene"
      viewBox="0 0 1000 600"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="sky" x2="0" y2="1">
          <stop stopColor="#a6b9b2" />
          <stop offset="1" stopColor="#d3c9ac" />
        </linearGradient>
        <linearGradient id="floor" x2="0" y2="1">
          <stop stopColor="#877f62" />
          <stop offset="1" stopColor="#343c31" />
        </linearGradient>
        <linearGradient id="wall" x2="1" y2="1">
          <stop stopColor="#a7a48a" />
          <stop offset="1" stopColor="#535b49" />
        </linearGradient>
        <radialGradient id="light">
          <stop stopColor="#f0d59b" stopOpacity=".65" />
          <stop offset="1" stopColor="#e1ce9c" stopOpacity="0" />
        </radialGradient>
        <filter id="grain">
          <feTurbulence
            baseFrequency=".65"
            numOctaves="3"
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="linear" slope=".065" />
          </feComponentTransfer>
          <feBlend in="SourceGraphic" mode="soft-light" />
        </filter>
      </defs>
      <g filter="url(#grain)">
        <path fill="url(#sky)" d="M0 0h1000v600H0z" />
        <path fill="url(#floor)" d="M0 310h1000v290H0z" />
        <path fill="#424b3c" d="M0 0h205v365L0 600z" />
        <path fill="url(#wall)" d="M205 0h585v338H205z" />
        <path fill="#65705b" d="M790 0h210v600L790 338z" />
        <path fill="#bdbaa0" d="M204 0h52v370l-52 17zM735 0h56v344l-56-5z" />
        <path fill="#384a3f" d="M290 78h405v236H290z" />
        <path
          fill="#839482"
          d="M307 91h102v207H307zM427 91h102v207H427zM548 91h130v207H548z"
        />
        <path
          stroke="#c6bfa0"
          strokeWidth="7"
          d="M417 80v235m121-235v235M290 183h405"
        />
        <path
          fill="#536b52"
          d="m290 268 61-81 34 53 60-132 75 147 58-73 45 66 70-102v163H290z"
        />
        <path fill="#8a8c6c" d="M256 320h479v24H256z" />
        <path fill="#535c47" d="m210 600 280-270 300 270z" />
        <path
          stroke="#a2a08a"
          opacity=".25"
          d="M0 507h1000M140 405h740M235 354h545M500 330 80 600M500 330l420 270M500 330v270"
        />
        <g fill="#343e31">
          <path d="M0 390V210q25-60 50 0v115q20-100 45-27v105zM859 372V214q30-67 55 0v110q22-77 48-16v95z" />
          <path d="M824 358h160l-26 111h-99zM-22 399h142L94 518H6z" />
        </g>
        <g fill="#577052">
          <ellipse cx="36" cy="201" rx="47" ry="80" />
          <ellipse cx="81" cy="270" rx="38" ry="73" />
          <ellipse cx="897" cy="196" rx="46" ry="85" />
          <ellipse cx="946" cy="274" rx="35" ry="69" />
        </g>
        <path fill="#a59976" d="m655 390 95 8 38 28-133-7z" />
        <path fill="#393f31" d="M666 418h8v60h-8zM766 427h8v61h-8z" />
        <path fill="#cbc29d" d="M77 0h846v23H77z" />
        <path fill="#4f5c49" d="M0 0h1000v42H0z" />
        <ellipse cx="515" cy="235" rx="360" ry="300" fill="url(#light)" />
      </g>
    </svg>
  );
}
