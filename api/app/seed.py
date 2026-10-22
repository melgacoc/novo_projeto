"""Seed idempotente: configurações, categorias, admin, usuários de desenvolvimento e dados de demonstração.

Uso: `python -m app.seed` (cria o que faltar). `python -m app.seed --no-demo` pula operadoras/passeios fictícios.
Os dados de demonstração são fictícios (operadoras e textos inventados, inspirados nos passeios mais vendidos do Rio).
"""
import sys
from datetime import date, datetime, time, timedelta
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.deps import DEV_EMAILS
from app.core.security import new_booking_code, now_utc
from app.models import (
    Booking,
    BookingItem,
    Category,
    Departure,
    Operator,
    OperatorMember,
    Payment,
    PlatformSetting,
    Tour,
    TourPhoto,
    TourPrice,
    TourPriceCategory,
    TourSchedule,
    TourTranslation,
    User,
)
from app.models.platform import DEFAULT_SETTINGS
from app.services import pricing, schedule_service, storage
from app.services.catalog_service import set_locations
from app.services.schedule_service import TZ

CATEGORIES = [
    ("barcos-e-praias", "Barcos e praias", "Barcos y playas", "Boats & beaches", "sailboat"),
    ("city-tour", "City tour", "City tour", "City tour", "landmark"),
    ("aventura", "Aventura", "Aventura", "Adventure", "mountain"),
    ("trilhas", "Trilhas", "Senderismo", "Hiking", "footprints"),
    ("cultura", "Cultura e comunidade", "Cultura y comunidad", "Culture & community", "users"),
    ("bate-volta", "Bate-volta", "Excursiones de un día", "Day trips", "bus"),
]

OPERATORS = [
    dict(public_name="Mar Azul Passeios", trade_name="Mar Azul Passeios Turísticos Ltda", document="00.000.000/0001-01",
         cadastur_number="DEMO-0001", contact_phone="+5521900000001", contact_email="contato@marazul.demo"),
    dict(public_name="Rota Carioca", trade_name="Rota Carioca Turismo", document="00.000.000/0001-02",
         cadastur_number="DEMO-0002", contact_phone="+5521900000002", contact_email="reservas@rotacarioca.demo"),
    dict(public_name="Pedra Alta Aventura", trade_name="Pedra Alta Esportes de Aventura", document="00.000.000/0001-03",
         cadastur_number="DEMO-0003", contact_phone="+5521900000003", contact_email="ola@pedraalta.demo"),
    dict(public_name="Comunidade Viva Tours", trade_name="Comunidade Viva Turismo de Base Comunitária",
         document="00.000.000/0001-04", cadastur_number="DEMO-0004", contact_phone="+5521900000004",
         contact_email="tour@comunidadeviva.demo"),
]


def T(title, summary, description, includes, excludes, bring, meeting):
    return dict(title=title, summary=summary, description=description, includes=includes, excludes=excludes,
                what_to_bring=bring, meeting_point_details=meeting)


TOURS = [
    dict(
        operator=0, category="bate-volta", slug="arraial-do-cabo-passeio-de-barco", duration=14 * 60,
        area="Copacabana", meeting=(-22.9711, -43.1863), address="Av. Atlântica, altura do Posto 4, Copacabana",
        cutoff=12 * 60, policy="flexible", fees="Taxa de embarque e de preservação (~R$ 35 por pessoa) paga no local",
        color=((2, 132, 199), (34, 211, 238)), max_pax=20,
        prices={"adult": (180_00, 0, 120), "child": (90_00, 6, 10), "infant": (0, 0, 5)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(7, 0), 40)],
        pt=T("Arraial do Cabo: o Caribe brasileiro em um dia",
             "Bate-volta com passeio de barco pelas praias de água cristalina de Arraial do Cabo.",
             "Saída cedo do Rio em van ou ônibus com ar-condicionado. Em Arraial, passeio de barco de cerca de 3 horas com paradas para banho na Prainha, Praia do Forno e Gruta Azul (quando o mar permite). Tempo livre para almoço e retorno no fim da tarde.",
             "Transporte ida e volta\nPasseio de barco\nGuia acompanhante", "Almoço\nTaxa de embarque",
             "Roupa de banho, protetor solar, toalha e dinheiro para o almoço", "Chegue 15 minutos antes. O guia estará com uma placa da Mar Azul."),
        es=T("Arraial do Cabo: el Caribe brasileño en un día",
             "Excursión de un día con paseo en barco por las playas de aguas cristalinas de Arraial do Cabo.",
             "Salida temprano de Río en van o bus con aire acondicionado. En Arraial, paseo en barco de unas 3 horas con paradas para bañarse en Prainha, Praia do Forno y la Gruta Azul (si el mar lo permite). Tiempo libre para almorzar y regreso al final de la tarde.",
             "Transporte ida y vuelta\nPaseo en barco\nGuía acompañante", "Almuerzo\nTasa de embarque",
             "Traje de baño, protector solar, toalla y dinero para el almuerzo", "Llega 15 minutos antes. El guía tendrá un cartel de Mar Azul."),
        en=T("Arraial do Cabo: the Brazilian Caribbean in one day",
             "Day trip with a boat tour through the crystal-clear beaches of Arraial do Cabo.",
             "Early departure from Rio by air-conditioned van or bus. In Arraial, a boat tour of about 3 hours with swimming stops at Prainha, Praia do Forno and the Blue Grotto (sea permitting). Free time for lunch and return in the late afternoon.",
             "Round-trip transport\nBoat tour\nTour guide", "Lunch\nBoarding fee",
             "Swimwear, sunscreen, towel and money for lunch", "Arrive 15 minutes early. The guide will hold a Mar Azul sign."),
    ),
    dict(
        operator=1, category="city-tour", slug="um-dia-no-rio-cristo-pao-de-acucar", duration=9 * 60,
        area="Copacabana", meeting=(-22.9690, -43.1822), address="Rua Barata Ribeiro, 200, Copacabana",
        cutoff=10 * 60, policy="flexible", fees="", color=((16, 185, 129), (5, 150, 105)), max_pax=12,
        prices={"adult": (420_00, 11, 59), "senior": (330_00, 60, 120), "child": (295_00, 3, 10), "infant": (0, 0, 2)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(8, 30), 25)],
        pt=T("Um Dia no Rio: Cristo Redentor, Pão de Açúcar e Selarón",
             "Os cartões-postais do Rio em um só dia, com ingressos incluídos.",
             "Visita ao Cristo Redentor (trem ou van oficial), almoço em restaurante típico, Escadaria Selarón, Catedral Metropolitana e bondinho do Pão de Açúcar no fim da tarde.",
             "Transporte\nIngressos do Cristo e do Pão de Açúcar\nAlmoço\nGuia bilíngue", "Bebidas",
             "Roupa confortável e documento com foto", "Encontro na portaria indicada no voucher."),
        es=T("Un Día en Río: Cristo Redentor, Pan de Azúcar y Selarón",
             "Las postales de Río en un solo día, con entradas incluidas.",
             "Visita al Cristo Redentor (tren o van oficial), almuerzo en restaurante típico, Escalera Selarón, Catedral Metropolitana y teleférico del Pan de Azúcar al final de la tarde.",
             "Transporte\nEntradas del Cristo y del Pan de Azúcar\nAlmuerzo\nGuía bilingüe", "Bebidas",
             "Ropa cómoda y documento con foto", "Encuentro en la recepción indicada en el voucher."),
        en=T("A Day in Rio: Christ the Redeemer, Sugarloaf and Selarón",
             "Rio's postcards in a single day, tickets included.",
             "Visit Christ the Redeemer (train or official van), lunch at a local restaurant, Selarón Steps, the Metropolitan Cathedral and the Sugarloaf cable car in the late afternoon.",
             "Transport\nChrist and Sugarloaf tickets\nLunch\nBilingual guide", "Drinks",
             "Comfortable clothes and photo ID", "Meet at the lobby indicated on the voucher."),
    ),
    dict(
        operator=2, category="aventura", slug="stand-up-paddle-praia-vermelha", duration=90,
        area="Urca", meeting=(-22.9551, -43.1647), address="Praia Vermelha, Urca (canto direito)",
        cutoff=8 * 60, policy="moderate", fees="", color=((249, 115, 22), (251, 191, 36)), max_pax=6,
        prices={"adult": (130_00, 12, 120), "child": (90_00, 8, 11)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(6, 0), 12), ([5, 6], time(8, 0), 12)],
        pt=T("Stand up paddle ao nascer do sol na Praia Vermelha",
             "Reme com vista para o Pão de Açúcar, com instrutor e equipamento.",
             "Aula rápida na areia e remada guiada pela enseada da Praia Vermelha, ao pé do Pão de Açúcar. Ideal para iniciantes.",
             "Prancha, remo e colete\nInstrutor\nFotos", "Transporte", "Roupa de banho e protetor solar",
             "Procure a tenda laranja da Pedra Alta no canto direito da praia."),
        es=T("Stand up paddle al amanecer en Praia Vermelha",
             "Rema con vista al Pan de Azúcar, con instructor y equipo.",
             "Clase rápida en la arena y remada guiada por la ensenada de Praia Vermelha, al pie del Pan de Azúcar. Ideal para principiantes.",
             "Tabla, remo y chaleco\nInstructor\nFotos", "Transporte", "Traje de baño y protector solar",
             "Busca la carpa naranja de Pedra Alta en el lado derecho de la playa."),
        en=T("Sunrise stand up paddle at Praia Vermelha",
             "Paddle with Sugarloaf views, instructor and gear included.",
             "Quick lesson on the sand and guided paddle around Praia Vermelha cove, at the foot of Sugarloaf Mountain. Great for beginners.",
             "Board, paddle and life vest\nInstructor\nPhotos", "Transport", "Swimwear and sunscreen",
             "Look for Pedra Alta's orange tent on the right side of the beach."),
    ),
    dict(
        operator=3, category="cultura", slug="tour-na-rocinha-com-guia-local", duration=3 * 60,
        area="São Conrado", meeting=(-22.9881, -43.2483), address="Estação São Conrado do metrô, saída A",
        cutoff=2 * 60, policy="flexible", fees="", color=((168, 85, 247), (236, 72, 153)), max_pax=10,
        prices={"adult": (170_00, 12, 120), "child": (85_00, 6, 11)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(9, 0), 15), ([0, 1, 2, 3, 4, 5, 6], time(14, 0), 15)],
        pt=T("Tour na Rocinha com guia morador",
             "Conheça a maior favela do Brasil com quem vive lá: história, arte e vista incrível.",
             "Caminhada guiada por moradores, com paradas em ateliês, mirantes e comércio local. Parte do valor fica com projetos sociais da comunidade.",
             "Guia morador\nMototáxi de subida\nDegustação local", "Fotos de moradores sem permissão",
             "Tênis e roupa leve", "Encontro na saída A do metrô São Conrado."),
        es=T("Tour en la Rocinha con guía local",
             "Conoce la favela más grande de Brasil con quien vive allí: historia, arte y una vista increíble.",
             "Caminata guiada por residentes, con paradas en talleres, miradores y comercios locales. Parte del valor va a proyectos sociales de la comunidad.",
             "Guía residente\nMototaxi de subida\nDegustación local", "Fotos de residentes sin permiso",
             "Zapatillas y ropa liviana", "Encuentro en la salida A del metro São Conrado."),
        en=T("Rocinha tour with a local guide",
             "Discover Brazil's largest favela with those who live there: history, art and an amazing view.",
             "Walking tour led by residents, with stops at art studios, viewpoints and local shops. Part of the price funds community projects.",
             "Resident guide\nMoto-taxi ride up\nLocal tasting", "Photos of residents without permission",
             "Sneakers and light clothes", "Meet at exit A of São Conrado subway station."),
    ),
    dict(
        operator=0, category="barcos-e-praias", slug="angra-dos-reis-escuna-pelas-ilhas", duration=13 * 60,
        area="Botafogo", meeting=(-22.9465, -43.1823), address="Praia de Botafogo, 400",
        cutoff=12 * 60, policy="flexible", fees="Taxa municipal de turismo (~R$ 28 por pessoa) paga no local",
        color=((14, 165, 233), (99, 102, 241)), max_pax=20,
        prices={"adult": (200_00, 11, 120), "child": (100_00, 6, 10), "infant": (0, 0, 5)},
        schedules=[([1, 2, 3, 4, 5, 6], time(7, 0), 40)],
        pt=T("Angra dos Reis: escuna pelas ilhas", "Dia de escuna pelas ilhas paradisíacas de Angra.",
             "Transporte do Rio até Angra e passeio de escuna com paradas na Lagoa Azul, Ilha da Botinas e praias de água verde.",
             "Transporte\nPasseio de escuna\nFrutas a bordo", "Almoço\nTaxa municipal",
             "Roupa de banho e protetor solar", "Embarque em frente ao número 400 da Praia de Botafogo."),
        es=T("Angra dos Reis: goleta por las islas", "Día en goleta por las islas paradisíacas de Angra.",
             "Transporte de Río a Angra y paseo en goleta con paradas en la Laguna Azul, Isla de Botinas y playas de agua verde.",
             "Transporte\nPaseo en goleta\nFrutas a bordo", "Almuerzo\nTasa municipal",
             "Traje de baño y protector solar", "Embarque frente al número 400 de Praia de Botafogo."),
        en=T("Angra dos Reis: schooner island hopping", "A day on a schooner through Angra's paradise islands.",
             "Transport from Rio to Angra and schooner tour with stops at the Blue Lagoon, Botinas Island and green-water beaches.",
             "Transport\nSchooner tour\nFruit on board", "Lunch\nMunicipal fee",
             "Swimwear and sunscreen", "Boarding in front of number 400, Praia de Botafogo."),
    ),
    dict(
        operator=1, category="city-tour", slug="corcovado-com-almoco", duration=6 * 60,
        area="Cosme Velho", meeting=(-22.9404, -43.1980), address="Rua Cosme Velho, 513",
        cutoff=6 * 60, policy="moderate", fees="", color=((34, 197, 94), (132, 204, 22)), max_pax=12,
        prices={"adult": (280_00, 11, 120), "child": (190_00, 6, 10), "infant": (0, 0, 5)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(9, 0), 20)],
        pt=T("Corcovado e Cristo Redentor com almoço", "Suba ao Cristo com guia e almoce com vista.",
             "Trem do Corcovado, visita ao Cristo Redentor e almoço em restaurante no Santa Teresa.",
             "Ingresso do trem\nGuia\nAlmoço", "Bebidas", "Documento com foto", "Encontro na estação do trem do Corcovado."),
        es=T("Corcovado y Cristo Redentor con almuerzo", "Sube al Cristo con guía y almuerza con vista.",
             "Tren del Corcovado, visita al Cristo Redentor y almuerzo en un restaurante de Santa Teresa.",
             "Entrada del tren\nGuía\nAlmuerzo", "Bebidas", "Documento con foto", "Encuentro en la estación del tren del Corcovado."),
        en=T("Corcovado and Christ the Redeemer with lunch", "Visit Christ the Redeemer with a guide and enjoy lunch with a view.",
             "Corcovado train, visit to Christ the Redeemer and lunch at a restaurant in Santa Teresa.",
             "Train ticket\nGuide\nLunch", "Drinks", "Photo ID", "Meet at the Corcovado train station."),
    ),
    dict(
        operator=2, category="aventura", slug="voo-de-asa-delta-pedra-bonita", duration=2 * 60,
        area="São Conrado", meeting=(-22.9997, -43.2654), address="Praia do Pepino, São Conrado",
        cutoff=4 * 60, policy="moderate", fees="", color=((239, 68, 68), (249, 115, 22)), max_pax=2,
        prices={"adult": (1300_00, 12, 120)},
        schedules=[([0, 1, 2, 3, 4, 5, 6], time(9, 0), 2), ([0, 1, 2, 3, 4, 5, 6], time(11, 0), 2),
                   ([0, 1, 2, 3, 4, 5, 6], time(13, 0), 2)],
        pt=T("Voo de asa-delta da Pedra Bonita", "Voo duplo com instrutor e pouso na Praia do Pepino.",
             "Decolagem da rampa da Pedra Bonita, voo de 10 a 15 minutos sobre a floresta e o mar, pouso na praia. Fotos e vídeo inclusos.",
             "Voo duplo\nTransporte até a rampa\nFotos e vídeo", "", "Tênis e roupa confortável",
             "Encontro na base da Pedra Alta, na Praia do Pepino."),
        es=T("Vuelo en ala delta desde Pedra Bonita", "Vuelo doble con instructor y aterrizaje en Praia do Pepino.",
             "Despegue desde la rampa de Pedra Bonita, vuelo de 10 a 15 minutos sobre el bosque y el mar, aterrizaje en la playa. Fotos y video incluidos.",
             "Vuelo doble\nTransporte a la rampa\nFotos y video", "", "Zapatillas y ropa cómoda",
             "Encuentro en la base de Pedra Alta, en Praia do Pepino."),
        en=T("Hang gliding from Pedra Bonita", "Tandem flight with an instructor, landing on Pepino Beach.",
             "Take off from the Pedra Bonita ramp, 10 to 15 minutes flying over the forest and the sea, landing on the beach. Photos and video included.",
             "Tandem flight\nTransport to the ramp\nPhotos and video", "", "Sneakers and comfortable clothes",
             "Meet at Pedra Alta's base on Pepino Beach."),
    ),
    dict(
        operator=2, category="trilhas", slug="trilha-pedra-do-telegrafo", duration=5 * 60,
        area="Barra de Guaratiba", meeting=(-23.0688, -43.5651), address="Praça de Barra de Guaratiba",
        cutoff=12 * 60, policy="flexible", fees="", color=((101, 163, 13), (21, 128, 61)), max_pax=8,
        prices={"adult": (170_00, 12, 120), "child": (120_00, 8, 11)},
        schedules=[([5, 6], time(6, 30), 15)],
        pt=T("Trilha da Pedra do Telégrafo", "A foto mais famosa do Rio, com guia e transporte.",
             "Trilha leve de 40 minutos até a Pedra do Telégrafo, com tempo para fotos e banho na Prainha do Perigoso.",
             "Guia\nTransporte\nÁgua", "Lanche", "Tênis, água e protetor solar", "Encontro na praça de Barra de Guaratiba."),
        es=T("Sendero de la Pedra do Telégrafo", "La foto más famosa de Río, con guía y transporte.",
             "Sendero fácil de 40 minutos hasta la Pedra do Telégrafo, con tiempo para fotos y baño en la Prainha do Perigoso.",
             "Guía\nTransporte\nAgua", "Merienda", "Zapatillas, agua y protector solar", "Encuentro en la plaza de Barra de Guaratiba."),
        en=T("Pedra do Telégrafo hike", "Rio's most famous photo spot, with guide and transport.",
             "Easy 40-minute hike to Pedra do Telégrafo, with time for photos and a swim at Prainha do Perigoso.",
             "Guide\nTransport\nWater", "Snack", "Sneakers, water and sunscreen", "Meet at Barra de Guaratiba square."),
    ),
]

LABELS = {
    "adult": ("Adulto", "Adulto", "Adult"),
    "child": ("Criança", "Niño", "Child"),
    "infant": ("Criança de colo", "Bebé", "Infant"),
    "senior": ("Idoso", "Adulto mayor", "Senior"),
}


def make_image(title: str, colors: tuple, variant: int) -> bytes:
    w, h = 1200, 800
    c1, c2 = colors if variant == 0 else (colors[1], colors[0])
    img = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
    for i in range(6):
        r = 120 + 60 * i
        draw.ellipse([w - r - 80 * variant, h - r, w + r - 80 * variant, h + r], outline=(255, 255, 255), width=2)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
    except OSError:
        font = ImageFont.load_default(size=54)
    words, lines, cur = title.split(), [], ""
    for word in words:
        if len(cur) + len(word) > 26:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    for i, line in enumerate(lines[:3]):
        draw.text((70, 90 + i * 72), line, fill=(255, 255, 255), font=font)
    out = BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def ensure_user(db, email: str, name: str, role: str, dev: bool) -> User:
    u = db.scalar(select(User).where(User.email == email))
    if not u:
        u = User(email=email, name=name, role=role, is_dev_user=dev, phone_e164="+5521999990000" if dev else None)
        db.add(u)
        db.flush()
    return u


def seed_base(db) -> None:
    for k, v in DEFAULT_SETTINGS.items():
        if not db.get(PlatformSetting, k):
            db.add(PlatformSetting(key=k, value=v))
    for i, (slug, pt, es, en, icon) in enumerate(CATEGORIES):
        if not db.scalar(select(Category).where(Category.slug == slug)):
            db.add(Category(slug=slug, name_pt=pt, name_es=es, name_en=en, icon=icon, position=i))
    ensure_user(db, settings.admin_email.lower(), settings.admin_name, "admin", dev=False)
    ensure_user(db, DEV_EMAILS["tourist"], "Turista Dev", "tourist", dev=True)
    ensure_user(db, DEV_EMAILS["operator"], "Operadora Dev", "operator", dev=True)
    ensure_user(db, DEV_EMAILS["admin"], "Admin Dev", "admin", dev=True)
    db.commit()


def seed_demo(db) -> None:
    dev_op_user = db.scalar(select(User).where(User.email == DEV_EMAILS["operator"]))
    ops: list[Operator] = []
    for data in OPERATORS:
        o = db.scalar(select(Operator).where(Operator.public_name == data["public_name"]))
        if not o:
            o = Operator(**data, legal_name=data["trade_name"], status="active")
            db.add(o)
            db.flush()
        if not db.scalar(select(OperatorMember).where(OperatorMember.operator_id == o.id,
                                                      OperatorMember.user_id == dev_op_user.id)):
            db.add(OperatorMember(operator_id=o.id, user_id=dev_op_user.id, role="owner"))
        ops.append(o)
    db.commit()

    cats = {c.slug: c for c in db.scalars(select(Category)).all()}
    today = schedule_service.today_local()
    for spec in TOURS:
        if db.scalar(select(Tour).where(Tour.slug == spec["slug"])):
            continue
        tour = Tour(
            operator_id=ops[spec["operator"]].id, category_id=cats[spec["category"]].id, slug=spec["slug"],
            status="published", duration_minutes=spec["duration"], min_pax_per_booking=1,
            max_pax_per_booking=spec["max_pax"], public_area_label=spec["area"],
            meeting_point_address=spec["address"], booking_cutoff_minutes=spec["cutoff"],
            cancellation_policy=spec["policy"], on_site_fees_note=spec["fees"],
        )
        set_locations(tour, *spec["meeting"])
        for loc in ("pt", "es", "en"):
            tour.translations.append(TourTranslation(locale=loc, **spec[loc]))
        for code, (cents, min_age, max_age) in spec["prices"].items():
            pt, es, en = LABELS[code]
            cat = TourPriceCategory(code=code, min_age=min_age, max_age=max_age, label_pt=pt, label_es=es, label_en=en)
            # temporada: preço de alta a partir de dezembro
            cat.prices.append(TourPrice(price_cents=cents, valid_from=today - timedelta(days=60),
                                        valid_to=date(today.year, 11, 30)))
            cat.prices.append(TourPrice(price_cents=int(cents * 1.15) // 100 * 100,
                                        valid_from=date(today.year, 12, 1), valid_to=None))
            tour.price_categories.append(cat)
        db.add(tour)
        db.flush()
        pricing.recompute_from_price(tour, today)
        for variant in (0, 1):
            content = make_image(spec["pt"]["title"], spec["color"], variant)
            key, url = storage.save_image(content, "image/jpeg", f"tours/{tour.id}")
            tour.photos.append(TourPhoto(url=url, storage_key=key, position=variant, alt=spec["pt"]["title"]))
        for weekdays, start, capacity in spec["schedules"]:
            db.add(TourSchedule(tour_id=tour.id, weekdays=weekdays, start_time=start, capacity=capacity,
                                valid_from=today - timedelta(days=1), valid_to=None))
        db.commit()
        schedule_service.generate_for_tour(db, tour)

    _demo_bookings(db)


def _demo_bookings(db) -> None:
    """Reservas de exemplo do turista dev: duas já realizadas (para testar repasses) e uma futura confirmada."""
    tourist = db.scalar(select(User).where(User.email == DEV_EMAILS["tourist"]))
    if db.scalar(select(Booking.id).where(Booking.user_id == tourist.id).limit(1)):
        return
    tours = {t.slug: t for t in db.scalars(select(Tour)).all()}
    plan = [
        ("tour-na-rocinha-com-guia-local", -5, time(9, 0), {"adult": 2}, "completed"),
        ("stand-up-paddle-praia-vermelha", -4, time(6, 0), {"adult": 1}, "completed"),
        ("um-dia-no-rio-cristo-pao-de-acucar", 3, time(8, 30), {"adult": 2, "child": 1}, "confirmed"),
    ]
    from app.services.booking_service import commission_rate_for
    from app.services.catalog_service import tour_text

    for slug, days, start, qty, status in plan:
        tour = tours[slug]
        op = db.get(Operator, tour.operator_id)
        starts_at = datetime.combine(schedule_service.today_local() + timedelta(days=days), start, tzinfo=TZ)
        dep = db.scalar(select(Departure).where(Departure.tour_id == tour.id, Departure.starts_at == starts_at))
        if not dep:
            dep = Departure(tour_id=tour.id, starts_at=starts_at, capacity=15, manually_edited=True, status="open")
            db.add(dep)
            db.flush()
        q = pricing.quote(tour, starts_at.date(), qty, "pt")
        rate = commission_rate_for(db, op)
        commission = round(q.subtotal_cents * rate)
        b = Booking(
            code=new_booking_code(), user_id=tourist.id, departure_id=dep.id, tour_id=tour.id, operator_id=op.id,
            status=status, locale="pt", contact_name="Turista Dev", contact_phone_e164="+5521999990000",
            contact_email=tourist.email, pax_total=q.pax_total, subtotal_cents=q.subtotal_cents,
            total_cents=q.subtotal_cents, commission_rate=rate, commission_cents=commission,
            operator_amount_cents=q.subtotal_cents - commission, paid_at=now_utc() - timedelta(days=10),
            confirmed_at=now_utc() - timedelta(days=10),
            completed_at=(starts_at + timedelta(hours=4)) if status == "completed" else None,
            snapshot={"title": tour_text(tour, "pt").title, "tour_slug": tour.slug, "starts_at": starts_at.isoformat(),
                      "duration_minutes": tour.duration_minutes, "area": tour.public_area_label,
                      "operator_name": op.public_name, "cancellation_policy": tour.cancellation_policy,
                      "on_site_fees_note": tour.on_site_fees_note},
            source="seed",
        )
        for line in q.lines:
            b.items.append(BookingItem(price_category_code=line.code, label=line.label, quantity=line.quantity,
                                       unit_price_cents=line.unit_price_cents))
        dep.seats_booked += q.pax_total
        db.add(b)
        db.flush()
        db.add(Payment(booking_id=b.id, gateway="fake", gateway_charge_id=f"fake_seed_{b.code}", method="pix",
                       status="approved", amount_cents=b.total_cents, fee_cents=round(b.total_cents * 0.0099)))
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_base(db)
        if "--no-demo" not in sys.argv:
            seed_demo(db)
    print("seed ok")


if __name__ == "__main__":
    main()
