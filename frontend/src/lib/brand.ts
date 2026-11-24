// Customer look & feel: name and logo text. Colors and font live in index.css
// (section "Kunden-Theme"). Replace both once the customer's corporate design
// is available.
export const brand = {
  product: 'Anfrageprüfung',
  customer: import.meta.env.VITE_CUSTOMER_NAME ?? 'Lehde',
  tagline: 'Anfrageunterlagen prüfen – Fakten, Widersprüche, Rückfragen',
}
