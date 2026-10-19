export type Format = "news" | "story" | "cards" | "test" | "podcast";

export type Photo = {
  src: string;
  alt: string;
  credit: string;
  page: string;
};

export type Question = {
  text: string;
  options: string[];
  answer: number;
  explanation: string;
};

export type Article = {
  slug: string;
  format: Format;
  title: string;
  lead: string;
  publishedAt: string;
  // Editor's pick for the lead slot on the home page.
  featured?: boolean;
  photo?: Photo;
  body: string[];
  // "cards" format: each card is a heading and its explanation.
  cards?: { title: string; text: string }[];
  // "test" format.
  questions?: Question[];
  // "podcast" format.
  duration?: string;
};

export const formats: Record<Format, { label: string; plural: string }> = {
  news: { label: "Новость", plural: "Новости" },
  story: { label: "История", plural: "Истории" },
  cards: { label: "Карточки", plural: "Карточки" },
  test: { label: "Тест", plural: "Тесты" },
  podcast: { label: "Подкаст", plural: "Подкасты" },
};

const photos = {
  embankment: {
    src: "/photos/embankment.webp",
    alt: "Набережная с фонарями и лестницами к реке осенью",
    credit: "Vyacheslav Bukharov, CC BY-SA 4.0, Wikimedia Commons",
    page: "https://commons.wikimedia.org/wiki/File:Ural_River_Embankment_in_Orenburg_(October_2025)_-_0_1.jpg",
  },
  tram: {
    src: "/photos/tram.webp",
    alt: "Красно-белый трамвай на проспекте зимним днём",
    credit: "Nikolai Bulykin, CC BY-SA 4.0, Wikimedia Commons",
    page: "https://commons.wikimedia.org/w/index.php?curid=145816028",
  },
  busStop: {
    src: "/photos/bus-stop.webp",
    alt: "Освещённый павильон остановки ночью среди сугробов",
    credit: "Лапоть, CC0, Wikimedia Commons",
    page: "https://commons.wikimedia.org/wiki/File:Shopping_center_bus_stop,_Vorkuta.jpg",
  },
  blocks: {
    src: "/photos/blocks.webp",
    alt: "Пятиэтажка, киоск и маршрутка на улице летом",
    credit: "Svetlov Artem, CC BY 3.0, Wikimedia Commons",
    page: "https://commons.wikimedia.org/wiki/File:Nelidovo,_Tver_Oblast,_Russia_-_panoramio_(16).jpg",
  },
  riverNight: {
    src: "/photos/river-night.webp",
    alt: "Мост через реку и огни города поздним вечером",
    credit: "Vyacheslav Argenberg, CC BY 4.0, Wikimedia Commons",
    page: "https://commons.wikimedia.org/wiki/File:Rostov-on-Don,_Don_River_at_night,_Russia.jpg",
  },
} satisfies Record<string, Photo>;

// Demo content: every article, name and number here is invented.
export const demoArticles: Article[] = [
  {
    slug: "embankment-opening",
    format: "news",
    featured: true,
    title: "Набережную откроют после реконструкции 1 ноября. Что на ней изменилось",
    lead: "Новые спуски к воде, освещение по всей длине и велодорожка до моста. Кафе у причала откроется только весной.",
    publishedAt: "2026-10-18T13:40:00+03:00",
    photo: photos.embankment,
    body: [
      "Работы на набережной шли полтора года. Подрядчик успел сдать участок от речного вокзала до моста, второй участок, до парка, закроют забором до весны.",
      "Главное изменение — три новых спуска к воде с широкими ступенями, на которых можно сидеть. Раньше к реке можно было выйти только у причала.",
      "Фонари теперь стоят по всей длине набережной, а не только у входа. Вдоль парапета проложили велодорожку, она выходит к мосту и соединяется с дорожкой на проспекте.",
      "Кафе в здании бывшего причала откроется весной: в администрации объяснили это тем, что арендатора ещё выбирают.",
    ],
  },
  {
    slug: "tram-intervals",
    format: "news",
    title: "С понедельника трамваи на двух линиях будут ходить реже",
    lead: "Интервал вырастет до 12 минут в часы пик. Транспортное управление объясняет это ремонтом путей на проспекте.",
    publishedAt: "2026-10-18T12:55:00+03:00",
    photo: photos.tram,
    body: [
      "Изменения коснутся третьей и седьмой линий. Вечером интервал останется прежним — около 15 минут.",
      "Ремонт путей на проспекте продлится две недели. На это время часть вагонов перевезут в другое депо.",
    ],
  },
  {
    slug: "hot-water-north",
    format: "news",
    title: "В северном районе отключат горячую воду с 21 по 23 октября",
    lead: "Без воды останутся около сорока домов: коммунальщики меняют участок трубы под улицей.",
    publishedAt: "2026-10-18T11:20:00+03:00",
    body: [
      "Список адресов опубликован на сайте управляющей компании. Воду обещают вернуть к вечеру четверга.",
    ],
  },
  {
    slug: "heated-stops",
    format: "news",
    title: "Первые остановки с подогревом поставили на окраинах",
    lead: "Павильоны закрытые, с прозрачными дверями и обогревом. Их ставят там, где автобус ходит реже раза в двадцать минут.",
    publishedAt: "2026-10-18T10:05:00+03:00",
    photo: photos.busStop,
    body: [
      "Пока таких остановок четыре. До конца года обещают ещё шесть — тоже на конечных и в спальных районах.",
      "Обогрев включается, когда на улице ниже нуля, и работает до последнего рейса.",
    ],
  },
  {
    slug: "school-bus",
    format: "news",
    title: "Для школьников из пригорода запустят бесплатный автобус",
    lead: "Маршрут будет ходить дважды утром и дважды днём, только по учебным дням.",
    publishedAt: "2026-10-18T09:30:00+03:00",
    body: ["Расписание согласуют с тремя школами, к которым идёт маршрут. Первый рейс — 3 ноября."],
  },
  {
    slug: "library-hours",
    format: "news",
    title: "Центральная библиотека будет открыта до 22:00",
    lead: "Продлённые часы — по будням. В читальном зале добавят розетки у каждого стола.",
    publishedAt: "2026-10-18T08:45:00+03:00",
    body: ["Решение приняли после опроса читателей: чаще всего просили вечерние часы."],
  },
  {
    slug: "fog-warning",
    format: "news",
    title: "Синоптики предупредили о густом тумане утром в воскресенье",
    lead: "Видимость местами упадёт до 100 метров. Водителям советуют закладывать время на дорогу.",
    publishedAt: "2026-10-18T07:50:00+03:00",
    body: ["Туман рассеется к полудню. Днём ожидается до +9 и без осадков."],
  },
  {
    slug: "five-storey",
    format: "story",
    title: "Дома, которые не снесут. Как живут пятиэтажки, исключённые из программы расселения",
    lead: "Жильцы ждали переезда восемь лет, а теперь узнали, что их дома признали пригодными. Мы поговорили с ними и с инженером, который проводил обследование.",
    publishedAt: "2026-10-17T19:00:00+03:00",
    photo: photos.blocks,
    body: [
      "В списке на расселение было двенадцать домов. В новой редакции программы их осталось пять: остальные семь после повторного обследования признали пригодными для жизни.",
      "Для жильцов это означает, что ремонт, который откладывали в ожидании переезда, придётся делать сейчас. В одном из домов крышу не меняли с момента постройки.",
      "Инженер, проводивший обследование, объясняет: несущие стены и перекрытия в хорошем состоянии, а проблемы с крышей и трубами решаются капитальным ремонтом.",
      "Жильцы собираются оспаривать решение. Первое собрание назначено на следующую субботу.",
    ],
  },
  {
    slug: "night-embankment",
    format: "story",
    title: "Город после девяти. Репортаж с ночной набережной",
    lead: "Кто гуляет у реки, когда закрываются кафе, и почему там стало спокойнее, чем пять лет назад.",
    publishedAt: "2026-10-16T21:00:00+03:00",
    photo: photos.riverNight,
    body: [
      "В половине десятого на набережной больше всего бегунов и собачников. К одиннадцати остаются компании у спусков к воде.",
      "Охранник у моста говорит, что за последние годы стало тише: появился свет, и вечерние прогулки перестали казаться рискованными.",
    ],
  },
  {
    slug: "parking-rules",
    format: "cards",
    title: "Новые правила парковки в центре. Объясняем в карточках",
    lead: "Что меняется с ноября, где парковка останется бесплатной и как оформить резидентское разрешение.",
    publishedAt: "2026-10-17T15:30:00+03:00",
    body: [],
    cards: [
      {
        title: "Что меняется?",
        text: "С 1 ноября парковка на улицах внутри бульварного кольца становится платной по будням с 8:00 до 20:00.",
      },
      {
        title: "Сколько это стоит?",
        text: "Первый час — 60 рублей, каждый следующий — 100. В выходные и праздники парковка бесплатная.",
      },
      {
        title: "Я живу в центре. Мне тоже платить?",
        text: "Нет, если оформить резидентское разрешение. Оно бесплатное и действует на улицах вашего квартала.",
      },
      {
        title: "Как оформить разрешение?",
        text: "Через портал госуслуг или в МФЦ. Нужны паспорт с регистрацией в центре и СТС автомобиля.",
      },
    ],
  },
  {
    slug: "guess-the-district",
    format: "test",
    title: "Узнаете ли вы свой город по трём подсказкам?",
    lead: "Три вопроса о местах, мимо которых вы ходите каждый день.",
    publishedAt: "2026-10-17T12:00:00+03:00",
    body: [],
    questions: [
      {
        text: "Откуда горожане чаще всего выходят к реке?",
        options: ["От речного вокзала", "От стадиона", "От рынка"],
        answer: 0,
        explanation: "До реконструкции набережной спуск к воде был только у причала речного вокзала.",
      },
      {
        text: "На какой транспорт пересаживаются у моста?",
        options: ["На электричку", "На трамвай", "На речной трамвай"],
        answer: 1,
        explanation: "У моста сходятся две трамвайные линии — третья и седьмая.",
      },
      {
        text: "Где поставили первые остановки с подогревом?",
        options: ["В центре", "У вокзала", "На окраинах"],
        answer: 2,
        explanation: "Их ставят там, где автобус ходит реже раза в двадцать минут.",
      },
    ],
  },
  {
    slug: "podcast-night-buses",
    format: "podcast",
    title: "Зачем городу ночные автобусы",
    lead: "Новый выпуск подкаста «Через остановку»: считаем, кто ездит после полуночи и во что обходится один рейс.",
    publishedAt: "2026-10-16T10:00:00+03:00",
    duration: "32 минуты",
    body: [
      "В выпуске — разговор с водителем ночного маршрута и с транспортным аналитиком.",
    ],
  },
];


const timeFormat = new Intl.DateTimeFormat("ru-RU", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Moscow",
});

const dateFormat = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  timeZone: "Europe/Moscow",
});

export function formatTime(iso: string) {
  return timeFormat.format(new Date(iso));
}

export function formatDate(iso: string) {
  return `${dateFormat.format(new Date(iso))}, ${formatTime(iso)}`;
}

export function formatDay(iso: string) {
  return dateFormat.format(new Date(iso));
}
