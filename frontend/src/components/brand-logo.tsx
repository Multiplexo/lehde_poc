/** Lehde logo rebuilt in CSS (yellow square, claim, bold italic name).
    Replace with the original logo file once the customer provides it. */
export function BrandLogo({ className = '' }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`inline-flex size-12 shrink-0 flex-col justify-between border border-brand bg-brand-accent px-1 pt-0.5 pb-0 text-brand ${className}`}>
      <span className="text-[5.5px] leading-none font-medium tracking-[0.04em] whitespace-nowrap">WIR BAUEN ZUKUNFT</span>
      <span className="-skew-x-6 text-[17px] leading-none font-black tracking-tighter">Lehde</span>
    </span>
  )
}
