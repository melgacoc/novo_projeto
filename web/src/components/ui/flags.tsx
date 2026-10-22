export function FlagBR({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 50" className={className}>
      <rect width="72" height="50" fill="#009b3a"/>
      <polygon points="36,4 68,25 36,46 4,25" fill="#fedf00"/>
      <circle cx="36" cy="25" r="14" fill="#002776"/>
    </svg>
  )
}

export function FlagES({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 500" className={className}>
      <rect width="750" height="500" fill="#c60b1e"/>
      <rect y="125" width="750" height="250" fill="#ffc400"/>
    </svg>
  )
}
export function FlagUS({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 76 40" className={className}>
      <rect width="76" height="40" fill="#b22234"/>
      {[1, 3, 5, 7, 9, 11].map((i) => (
        <rect key={i} y={(i * 40) / 13} width="76" height={40 / 13} fill="#fff"/>
      ))}
      <rect width="30.4" height={(7 * 40) / 13} fill="#3c3b6e"/>
    </svg>
  )
}
