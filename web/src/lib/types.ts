export type Lang = 'pt' | 'es' | 'en'

export type AppConfig = {
  app_name: string
  env: string
  auth_enabled: boolean
  google_login: boolean
  payment_gateway: string
  locales: Lang[]
  hold_minutes: number
  map: { style_url: string; center: [number, number] }
}

export type Category = { id: number; slug: string; name: string; icon: string; name_pt: string; name_es: string; name_en: string; position: number }

export type TourCard = {
  id: number
  slug: string
  title: string
  summary: string
  category: Category | null
  area: string
  lat: number | null
  lng: number | null
  from_price_cents: number | null
  duration_minutes: number
  photo: string | null
  rating_avg: number | null
  rating_count: number
  operator_name: string | null
  next_departure: string | null
  distance_m: number | null
}

export type PriceCategoryPublic = { code: string; label: string; min_age: number; max_age: number; price_cents_today: number | null }

export type TourDetail = TourCard & {
  description: string
  includes: string
  excludes: string
  what_to_bring: string
  photos: { url: string; alt: string }[]
  price_categories: PriceCategoryPublic[]
  min_pax_per_booking: number
  max_pax_per_booking: number
  booking_cutoff_minutes: number
  cancellation_policy: 'flexible' | 'moderate' | 'strict'
  on_site_fees_note: string
  instant_booking: boolean
  available_locales: Lang[]
}

export type DeparturePublic = { id: number; starts_at: string; date: string; time: string; availability: 'available' | 'last_seats' | 'sold_out' }

export type Page<T> = { items: T[]; total: number; page: number; page_size: number }

export type Payment = {
  id: number
  method: 'pix' | 'card'
  status: string
  amount_cents: number
  gateway: string
  charge_id: string
  pix_qr_code: string | null
  pix_expires_at: string | null
  checkout_url: string | null
}

export type Booking = {
  code: string
  status: 'held' | 'awaiting_operator' | 'confirmed' | 'expired' | 'cancelled' | 'no_show' | 'completed'
  tour_id: number
  tour_slug: string
  title: string
  area: string
  starts_at: string
  duration_minutes: number
  operator_name: string
  cancellation_policy: string
  on_site_fees_note: string
  pax_total: number
  items: { code: string; label: string; quantity: number; unit_price_cents: number }[]
  total_cents: number
  refund_amount_cents: number
  hold_expires_at: string | null
  paid_at: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancelled_by: string | null
  cancel_reason: string | null
  locale: Lang
  contact_name: string
  created_at: string
  payments: Payment[]
  refund_if_cancelled_now_cents?: number | null
  private?: {
    meeting_point_address: string
    meeting_point_details: string
    meeting_lat: number | null
    meeting_lng: number | null
    operator_trade_name: string
    operator_phone: string
    operator_email: string
  }
  // operadora/admin
  contact_phone?: string
  contact_email?: string
  commission_rate?: number
  commission_cents?: number
  operator_amount_cents?: number
  operator_id?: number
  departure_id?: number
  source?: string | null
}

export type Me = {
  id: number
  email: string
  name: string
  phone: string | null
  role: 'tourist' | 'operator' | 'admin'
  locale: Lang
  is_dev_user: boolean
  operators: { id: number; public_name: string; status: string }[]
}

export type DepartureOperator = {
  id: number
  tour_id: number
  schedule_id: number | null
  starts_at: string
  date: string
  time: string
  capacity: number
  seats_held: number
  seats_booked: number
  seats_available: number
  status: 'open' | 'closed' | 'cancelled'
  cancel_reason: string | null
  manually_edited: boolean
  title?: string
}

export type Translation = {
  locale: Lang
  title: string
  summary: string
  description: string
  includes: string
  excludes: string
  what_to_bring: string
  meeting_point_details: string
}

export type PriceCategoryFull = {
  code: 'adult' | 'child' | 'infant' | 'senior'
  min_age: number
  max_age: number
  label_pt: string
  label_es: string
  label_en: string
  prices: { price_cents: number; valid_from: string; valid_to: string | null }[]
}

export type Schedule = { id: number; weekdays: number[]; start_time: string; capacity: number; valid_from: string; valid_to: string | null }

export type TourFull = {
  id: number
  operator_id: number
  slug: string
  status: 'draft' | 'pending_review' | 'published' | 'paused' | 'rejected'
  category_id: number | null
  duration_minutes: number
  min_pax_per_booking: number
  max_pax_per_booking: number
  public_area_label: string
  public_lat: number | null
  public_lng: number | null
  meeting_point_address: string
  meeting_lat: number | null
  meeting_lng: number | null
  booking_cutoff_minutes: number
  instant_booking: boolean
  cancellation_policy: 'flexible' | 'moderate' | 'strict'
  on_site_fees_note: string
  from_price_cents: number | null
  review_notes: string
  translations: Translation[]
  photos: { id: number; url: string; position: number; alt: string }[]
  price_categories: PriceCategoryFull[]
  schedules: Schedule[]
  title: string
  created_at?: string
  updated_at?: string
  problems?: string[]
  contact_flags?: { field: string; kind: string; match: string }[]
  operator_name?: string
}
