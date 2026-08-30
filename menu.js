/* ============================================================
   LAZZA — настройки и меню
   Это главный файл владельца кафе. Надписи интерфейса — в i18n.js.

   У каждого названия и описания три языка: az / ru / en.
   Заполняйте все три — гость увидит тот, который выберет.
   ============================================================ */

const CONFIG = {
  name: 'Lazza',

  /* ВАЖНО: номер WhatsApp, куда приходят заказы.
     Только цифры, с кодом страны, без «+», пробелов и скобок.
     Азербайджан: 994 + номер без нуля. Например: 994501234567 */
  whatsapp: '994501234567',

  phone: '+994 50 123 45 67',
  instagram: 'lazza.cafe',        // ник без «@»

  address: {
    az: 'Heydər Əliyev küçəsi, 12',
    ru: 'Ул. Гейдара Алиева, 12',
    en: 'Heydar Aliyev street, 12',
  },
  city: { az: 'Bakı', ru: 'Баку', en: 'Baku' },
  hours: {
    az: 'Hər gün 09:00 – 23:00',
    ru: 'Ежедневно 09:00 – 23:00',
    en: 'Daily 09:00 – 23:00',
  },

  openFrom: 9,   // час открытия (0–23), по нему считается индикатор «Открыто»
  openTo: 23,    // час закрытия
  mapUrl: 'https://yandex.com/maps/?text=Bakı, Heydər Əliyev küçəsi 12',

  currency: '₼',
  deliveryFee: 5,        // стоимость доставки
  freeDeliveryFrom: 40,  // бесплатно от этой суммы
  minOrder: 15,          // минимальная сумма заказа на доставку

  defaultLang: 'az',     // язык до выбора гостя: az / ru / en

  /* Тема до выбора гостя: 'dark' — фирменная тёмная, 'light' — светлая,
     'auto' — как настроен телефон гостя. Переключатель есть в любом случае. */
  defaultTheme: 'dark',
};

/* Наборы модификаторов — чтобы не повторять их у каждой позиции */
const MODS = {
  burgerExtras: {
    id: 'extras', type: 'multi',
    title: { az: 'Əlavələr', ru: 'Добавки', en: 'Extras' },
    choices: [
      { price: 3.50, name: { az: 'Əlavə kotlet', ru: 'Дополнительная котлета', en: 'Extra patty' } },
      { price: 1.50, name: { az: 'Bekon', ru: 'Бекон', en: 'Bacon' } },
      { price: 1.00, name: { az: 'İkiqat çedder', ru: 'Двойной чеддер', en: 'Double cheddar' } },
      { price: 0.80, name: { az: 'Xalapenyo', ru: 'Халапеньо', en: 'Jalapeño' } },
      { price: 1.00, name: { az: 'Lazza sousu', ru: 'Соус Lazza', en: 'Lazza sauce' } },
    ],
  },

  friesSize: {
    id: 'size', type: 'single', required: true,
    title: { az: 'Porsiya', ru: 'Порция', en: 'Size' },
    choices: [
      { price: 0, name: { az: 'Standart', ru: 'Стандарт', en: 'Regular' } },
      { price: 1.50, name: { az: 'Böyük', ru: 'Большая', en: 'Large' } },
    ],
  },

  cupSize: {
    id: 'size', type: 'single', required: true,
    title: { az: 'Həcm', ru: 'Объём', en: 'Cup size' },
    choices: [
      { price: 0, name: { az: '250 ml', ru: '250 мл', en: '250 ml' } },
      { price: 1.00, name: { az: '350 ml', ru: '350 мл', en: '350 ml' } },
      { price: 2.00, name: { az: '450 ml', ru: '450 мл', en: '450 ml' } },
    ],
  },

  milk: {
    id: 'milk', type: 'single', required: true,
    title: { az: 'Süd', ru: 'Молоко', en: 'Milk' },
    choices: [
      { price: 0, name: { az: 'Adi', ru: 'Обычное', en: 'Regular' } },
      { price: 1.00, name: { az: 'Laktozasız', ru: 'Безлактозное', en: 'Lactose-free' } },
      { price: 1.20, name: { az: 'Yulaf', ru: 'Овсяное', en: 'Oat' } },
      { price: 1.20, name: { az: 'Badam', ru: 'Миндальное', en: 'Almond' } },
    ],
  },

  syrup: {
    id: 'syrup', type: 'multi',
    title: { az: 'Sirop', ru: 'Сироп', en: 'Syrup' },
    choices: [
      { price: 1.00, name: { az: 'Karamel', ru: 'Карамель', en: 'Caramel' } },
      { price: 1.00, name: { az: 'Vanil', ru: 'Ваниль', en: 'Vanilla' } },
      { price: 1.00, name: { az: 'Meşə fındığı', ru: 'Лесной орех', en: 'Hazelnut' } },
    ],
  },
};

/* ============================================================
   МЕНЮ

   price  — цена в манатах
   old    — старая цена, показывается зачёркнутой
   img    — путь к фото
   weight — { v: число, u: 'g' | 'ml' | 'pcs' | 'kg' }
   tag    — 'hit' | 'new' | 'deal'; делает карточку крупной
   ============================================================ */

const MENU = [
  {
    id: 'burgers',
    title: { az: 'Burgerlər', ru: 'Бургеры', en: 'Burgers' },
    note: {
      az: 'Mal əti hər səhər doğranır, kotlet kömürdə bişirilir',
      ru: 'Говядина рубится каждое утро, котлета жарится на углях',
      en: 'Beef minced every morning, patties grilled over charcoal',
    },
    items: [
      {
        id: 'b1', price: 9.90, img: 'images/burger-classic.jpg',
        weight: { v: 240, u: 'g' }, kcal: 620, tag: 'hit',
        name: { az: 'Lazza Classic', ru: 'Lazza Classic', en: 'Lazza Classic' },
        desc: {
          az: 'Kömürdə bişmiş mal əti kotleti, çedder, marinadlanmış xiyar, qırmızı soğan və firma Lazza sousu.',
          ru: 'Котлета из говядины на углях, чеддер, маринованный огурец, красный лук и фирменный соус Lazza.',
          en: 'Charcoal-grilled beef patty, cheddar, pickles, red onion and our own Lazza sauce.',
        },
        mods: [MODS.burgerExtras],
      },
      {
        id: 'b2', price: 13.50, img: 'images/burger-double.jpg',
        weight: { v: 340, u: 'g' }, kcal: 890,
        name: { az: 'Dabl Çiz', ru: 'Дабл Чиз', en: 'Double Cheese' },
        desc: {
          az: 'İki kotlet, ikiqat çedder, qırmızı soğan və xardal sousu. Ac gələnlər üçün.',
          ru: 'Две котлеты, двойной чеддер, красный лук и горчичный соус. Для тех, кто пришёл голодным.',
          en: 'Two patties, double cheddar, red onion and mustard sauce. For when you arrive hungry.',
        },
        mods: [MODS.burgerExtras],
      },
      {
        id: 'b3', price: 12.50, img: 'images/burger-bacon.jpg',
        weight: { v: 300, u: 'g' }, kcal: 780,
        name: { az: 'Bekon Smoki', ru: 'Бекон Смоки', en: 'Smoky Bacon' },
        desc: {
          az: 'Xırtıldayan bekon, hisə verilmiş pendir, pomidor və barbekü sousu.',
          ru: 'Хрустящий бекон, копчёный сыр, томат и соус барбекю на углях.',
          en: 'Crispy bacon, smoked cheese, tomato and barbecue sauce.',
        },
        mods: [MODS.burgerExtras],
      },
      {
        id: 'b4', price: 9.50, img: 'images/burger-chicken.jpg',
        weight: { v: 280, u: 'g' }, kcal: 640,
        name: { az: 'Çiken Krispi', ru: 'Чикен Криспи', en: 'Crispy Chicken' },
        desc: {
          az: 'Xırtıldayan qırıntıda toyuq filesi, aysberq, pomidor və pendir sousu.',
          ru: 'Куриное филе в хрустящей панировке, айсберг, томат и сырный соус.',
          en: 'Crumbed chicken fillet, iceberg lettuce, tomato and cheese sauce.',
        },
        mods: [MODS.burgerExtras],
      },
      {
        id: 'b5', price: 11.90, img: 'images/burger-cheddar.jpg',
        weight: { v: 290, u: 'g' }, kcal: 710,
        name: { az: 'Çedder Melt', ru: 'Чеддер Мелт', en: 'Cheddar Melt' },
        desc: {
          az: 'Əriyən çedder, duza qoyulmuş xiyar, xırtıldayan soğan fri və dijon xardalı.',
          ru: 'Расплавленный чеддер, солёные огурцы, хрустящий лук фри и дижонская горчица.',
          en: 'Melted cheddar, pickles, crispy fried onion and Dijon mustard.',
        },
        mods: [MODS.burgerExtras],
      },
      {
        id: 'b6', price: 16.50, img: 'images/burger-craft.jpg',
        weight: { v: 330, u: 'g' }, kcal: 820, tag: 'new',
        name: { az: 'Blek Anqus', ru: 'Блэк Ангус', en: 'Black Angus' },
        desc: {
          az: 'Mərmər mal ətindən kotlet, rukola, qurudulmuş pomidor və trüfel mayonezi.',
          ru: 'Котлета из мраморной говядины, руккола, вяленый томат и трюфельный майонез.',
          en: 'Marbled beef patty, rocket, sun-dried tomato and truffle mayo.',
        },
        mods: [MODS.burgerExtras],
      },
    ],
  },

  {
    id: 'combo',
    title: { az: 'Kombo', ru: 'Комбо', en: 'Combos' },
    note: {
      az: 'Yığılmış dəst ayrı-ayrılıqda alınandan ucuzdur',
      ru: 'Собранный набор дешевле, чем по отдельности',
      en: 'A set costs less than the same items apart',
    },
    items: [
      {
        id: 'c1', price: 14.90, old: 18.50, img: 'images/combo-classic.jpg',
        weight: { v: 620, u: 'g' }, tag: 'deal',
        name: { az: 'Kombo Klassik', ru: 'Комбо Классик', en: 'Classic Combo' },
        desc: {
          az: 'Lazza Classic, kartof fri və seçim üzrə içki.',
          ru: 'Lazza Classic, картофель фри и напиток на выбор.',
          en: 'Lazza Classic, fries and a drink of your choice.',
        },
        mods: [{
          id: 'drink', type: 'single', required: true,
          title: { az: 'İçki', ru: 'Напиток', en: 'Drink' },
          choices: [
            { price: 0, name: { az: 'Kola', ru: 'Кола', en: 'Cola' } },
            { price: 0.50, name: { az: 'Limonad', ru: 'Лимонад', en: 'Lemonade' } },
            { price: 0.80, name: { az: 'Amerikano', ru: 'Американо', en: 'Americano' } },
            { price: 1.50, name: { az: 'Kapuçino', ru: 'Капучино', en: 'Cappuccino' } },
          ],
        }],
      },
      {
        id: 'c2', price: 27.90, old: 33.50, img: 'images/combo-duo.jpg',
        weight: { v: 1.2, u: 'kg' },
        name: { az: 'İki nəfərlik kombo', ru: 'Комбо на двоих', en: 'Combo for two' },
        desc: {
          az: 'Seçim üzrə iki burger, böyük kartof fri, soğan halqaları və iki içki.',
          ru: 'Два бургера на выбор, большая порция фри, луковые кольца и два напитка.',
          en: 'Two burgers of your choice, large fries, onion rings and two drinks.',
        },
        mods: [{
          id: 'burgers', type: 'single', required: true,
          title: { az: 'Burgerlər', ru: 'Бургеры', en: 'Burgers' },
          choices: [
            { price: 0, name: { az: 'İki Lazza Classic', ru: 'Два Lazza Classic', en: 'Two Lazza Classic' } },
            { price: 2.00, name: { az: 'Classic + Bekon Smoki', ru: 'Classic + Бекон Смоки', en: 'Classic + Smoky Bacon' } },
            { price: 5.00, name: { az: 'İki Dabl Çiz', ru: 'Два Дабл Чиз', en: 'Two Double Cheese' } },
          ],
        }],
      },
      {
        id: 'c3', price: 18.90, old: 22.50, img: 'images/combo-shake.jpg',
        weight: { v: 780, u: 'g' },
        name: { az: 'Kokteyllə kombo', ru: 'Комбо с шейком', en: 'Shake Combo' },
        desc: {
          az: 'Bekon Smoki, pendirli fri və süd kokteyli.',
          ru: 'Бекон Смоки, фри с сыром и молочный коктейль.',
          en: 'Smoky Bacon, cheese fries and a milkshake.',
        },
        mods: [{
          id: 'shake', type: 'single', required: true,
          title: { az: 'Kokteylin dadı', ru: 'Вкус коктейля', en: 'Shake flavour' },
          choices: [
            { price: 0, name: { az: 'Şokolad', ru: 'Шоколад', en: 'Chocolate' } },
            { price: 0, name: { az: 'Vanil', ru: 'Ваниль', en: 'Vanilla' } },
            { price: 0, name: { az: 'Çiyələk', ru: 'Клубника', en: 'Strawberry' } },
            { price: 0.80, name: { az: 'Oreo', ru: 'Орео', en: 'Oreo' } },
          ],
        }],
      },
    ],
  },

  {
    id: 'fries',
    title: { az: 'Kartof və qəlyanaltı', ru: 'Фри и снеки', en: 'Fries & snacks' },
    note: {
      az: 'Porsiyalarla qızardırıq — isti gətiririk',
      ru: 'Обжариваем порционно — приносим горячими',
      en: 'Fried to order — served hot',
    },
    items: [
      {
        id: 'f1', price: 4.50, img: 'images/fries-classic.jpg',
        weight: { v: 150, u: 'g' }, kcal: 380,
        name: { az: 'Kartof fri', ru: 'Картофель фри', en: 'French fries' },
        desc: {
          az: 'Nazik doğranmış, dəniz duzu ilə. Yaxşılaşdırmağa ehtiyacı olmayan klassika.',
          ru: 'Тонкая соломка, морская соль. Классика, которую не нужно улучшать.',
          en: 'Thin cut, sea salt. The classic that needs no improving.',
        },
        mods: [MODS.friesSize],
      },
      {
        id: 'f2', price: 7.50, img: 'images/fries-cheese.jpg',
        weight: { v: 210, u: 'g' }, kcal: 520, tag: 'hit',
        name: { az: 'Pendirli və trüfellı fri', ru: 'Фри с сыром и трюфелем', en: 'Truffle cheese fries' },
        desc: {
          az: 'Pendir sousu, trüfel yağı və parmezanla kartof fri.',
          ru: 'Картофель фри под сырным соусом с трюфельным маслом и пармезаном.',
          en: 'Fries under cheese sauce with truffle oil and parmesan.',
        },
        mods: [MODS.friesSize],
      },
      {
        id: 'f3', price: 5.50, img: 'images/fries-rustic.jpg',
        weight: { v: 200, u: 'g' }, kcal: 420,
        name: { az: 'Kənd üsulu kartof', ru: 'Фри по-деревенски', en: 'Rustic potatoes' },
        desc: {
          az: 'Qabığında dilimlənmiş kartof, rozmarin və sarımsaqla.',
          ru: 'Дольки картофеля в кожуре с розмарином и чесноком.',
          en: 'Skin-on potato wedges with rosemary and garlic.',
        },
        mods: [MODS.friesSize],
      },
      {
        id: 'f4', price: 6.50, img: 'images/onion-rings.jpg',
        weight: { v: 180, u: 'g' }, kcal: 460,
        name: { az: 'Soğan halqaları', ru: 'Луковые кольца', en: 'Onion rings' },
        desc: {
          az: 'Şirin soğan xırtıldayan xəmirdə, ranç sousu ilə veririk.',
          ru: 'Сладкий лук в хрустящем кляре, подаём с соусом ранч.',
          en: 'Sweet onion in crispy batter, served with ranch.',
        },
      },
      {
        id: 'f5', price: 6.90, img: 'images/nuggets.jpg',
        weight: { v: 6, u: 'pcs' },
        name: { az: 'Toyuq naqetsləri', ru: 'Куриные наггетсы', en: 'Chicken nuggets' },
        desc: {
          az: 'Qırıntıda toyuq filesi parçaları, seçim üzrə sous.',
          ru: 'Кусочки куриного филе в панировке, соус на выбор.',
          en: 'Crumbed chicken pieces with a sauce of your choice.',
        },
        mods: [
          {
            id: 'count', type: 'single', required: true,
            title: { az: 'Say', ru: 'Количество', en: 'Pieces' },
            choices: [
              { price: 0, name: { az: '6 ədəd', ru: '6 штук', en: '6 pieces' } },
              { price: 2.50, name: { az: '9 ədəd', ru: '9 штук', en: '9 pieces' } },
              { price: 4.50, name: { az: '12 ədəd', ru: '12 штук', en: '12 pieces' } },
            ],
          },
          {
            id: 'sauce', type: 'single', required: true,
            title: { az: 'Sous', ru: 'Соус', en: 'Sauce' },
            choices: [
              { price: 0, name: { az: 'Turş-şirin', ru: 'Кисло-сладкий', en: 'Sweet & sour' } },
              { price: 0, name: { az: 'Pendirli', ru: 'Сырный', en: 'Cheese' } },
              { price: 0, name: { az: 'Barbekü', ru: 'Барбекю', en: 'Barbecue' } },
              { price: 0, name: { az: 'Acı', ru: 'Острый', en: 'Hot' } },
            ],
          },
        ],
      },
      {
        id: 'f6', price: 8.90, img: 'images/strips.jpg',
        weight: { v: 250, u: 'g' }, kcal: 560,
        name: { az: 'Toyuq stripsləri', ru: 'Куриные стрипсы', en: 'Chicken strips' },
        desc: {
          az: 'Qarğıdalı ləpəsində toyuq filesi zolaqları, iki sousla veririk.',
          ru: 'Полоски куриного филе в хлопьях кукурузы, подаём с двумя соусами.',
          en: 'Chicken strips in corn flakes, served with two sauces.',
        },
      },
    ],
  },

  {
    id: 'coffee',
    title: { az: 'Qəhvə', ru: 'Кофе', en: 'Coffee' },
    note: {
      az: 'Bu həftənin qovurması, Braziliya ərəbikası',
      ru: 'Обжарка на этой неделе, бразильская арабика',
      en: 'Roasted this week, Brazilian arabica',
    },
    items: [
      {
        id: 'k1', price: 3.00, img: 'images/espresso.jpg',
        weight: { v: 40, u: 'ml' },
        name: { az: 'Espresso', ru: 'Эспрессо', en: 'Espresso' },
        desc: {
          az: 'İkiqat porsiya. Sıx, kakao və qurudulmuş gilas notları ilə.',
          ru: 'Двойная порция. Плотный, с нотами какао и сушёной вишни.',
          en: 'Double shot. Dense, with cocoa and dried cherry notes.',
        },
      },
      {
        id: 'k2', price: 3.50, img: 'images/americano.jpg',
        weight: { v: 250, u: 'ml' },
        name: { az: 'Amerikano', ru: 'Американо', en: 'Americano' },
        desc: {
          az: 'Espresso və isti su. Südü ayrıca istəyə bilərsiniz.',
          ru: 'Эспрессо с горячей водой. Можно попросить молоко отдельно.',
          en: 'Espresso with hot water. Milk on the side if you ask.',
        },
        mods: [MODS.cupSize],
      },
      {
        id: 'k3', price: 4.50, img: 'images/cappuccino.jpg',
        weight: { v: 250, u: 'ml' }, tag: 'hit',
        name: { az: 'Kapuçino', ru: 'Капучино', en: 'Cappuccino' },
        desc: {
          az: 'Espresso və sıx süd köpüyü. Ən çox sifariş olunan qəhvəmiz.',
          ru: 'Эспрессо и плотная молочная пена. Наш самый заказываемый кофе.',
          en: 'Espresso and dense milk foam. The one we pour most often.',
        },
        mods: [MODS.cupSize, MODS.milk, MODS.syrup],
      },
      {
        id: 'k4', price: 5.00, img: 'images/latte.jpg',
        weight: { v: 350, u: 'ml' },
        name: { az: 'Latte', ru: 'Латте', en: 'Latte' },
        desc: {
          az: 'Yumşaq, südlü, nazik köpük və rəsmlə.',
          ru: 'Мягкий, молочный, с тонкой пенкой и рисунком.',
          en: 'Soft and milky, with thin foam and latte art.',
        },
        mods: [MODS.cupSize, MODS.milk, MODS.syrup],
      },
      {
        id: 'k5', price: 5.20, img: 'images/flat-white.jpg',
        weight: { v: 250, u: 'ml' },
        name: { az: 'Flet Vayt', ru: 'Флэт Уайт', en: 'Flat White' },
        desc: {
          az: 'İkiqat espresso və mikroköpük. Latteden güclü, amerikanodan yumşaq.',
          ru: 'Двойной эспрессо и микропена. Крепче латте, мягче американо.',
          en: 'Double espresso and microfoam. Stronger than latte, softer than americano.',
        },
        mods: [MODS.milk],
      },
      {
        id: 'k6', price: 6.00, img: 'images/raf.jpg',
        weight: { v: 300, u: 'ml' },
        name: { az: 'Raf', ru: 'Раф', en: 'Raf coffee' },
        desc: {
          az: 'Espresso, qaymaq və vanil şəkəri birlikdə çalınır.',
          ru: 'Эспрессо, сливки и ванильный сахар, взбитые вместе.',
          en: 'Espresso, cream and vanilla sugar whipped together.',
        },
        mods: [MODS.syrup],
      },
      {
        id: 'k7', price: 5.50, img: 'images/iced-latte.jpg',
        weight: { v: 400, u: 'ml' },
        name: { az: 'Ays Latte', ru: 'Айс Латте', en: 'Iced Latte' },
        desc: {
          az: 'Espresso, soyuq süd və buz. Yayda ilk qurtaran budur.',
          ru: 'Эспрессо, холодное молоко и лёд. Летом заканчивается первым.',
          en: 'Espresso, cold milk and ice. First to sell out in summer.',
        },
        mods: [MODS.milk, MODS.syrup],
      },
      {
        id: 'k8', price: 6.00, img: 'images/cold-brew.jpg',
        weight: { v: 400, u: 'ml' }, tag: 'new',
        name: { az: 'Kold Bryu', ru: 'Колд Брю', en: 'Cold Brew' },
        desc: {
          az: '16 saat soyuq suda dəmlənir. Acılıq yoxdur, giləmeyvə turşuluğu var.',
          ru: 'Настаиваем 16 часов на холодной воде. Без горечи, с ягодной кислинкой.',
          en: 'Steeped 16 hours in cold water. No bitterness, a berry tang.',
        },
      },
    ],
  },

  {
    id: 'drinks',
    title: { az: 'İçkilər', ru: 'Напитки', en: 'Drinks' },
    note: {
      az: 'Limonadları özümüz bişiririk, freşləri yanınızda sıxırıq',
      ru: 'Лимонады варим сами, фреши отжимаем при вас',
      en: 'Lemonades made in-house, juices pressed in front of you',
    },
    items: [
      {
        id: 'd1', price: 6.50, img: 'images/matcha.jpg',
        weight: { v: 350, u: 'ml' },
        name: { az: 'Matça Latte', ru: 'Матча Латте', en: 'Matcha Latte' },
        desc: {
          az: 'Mərasim matçası süddə. Yumşaq, ot acılığı olmadan.',
          ru: 'Церемониальная матча на молоке. Мягкая, без травяной горечи.',
          en: 'Ceremonial matcha with milk. Smooth, no grassy bitterness.',
        },
        mods: [MODS.milk],
      },
      {
        id: 'd2', price: 5.50, img: 'images/cocoa.jpg',
        weight: { v: 300, u: 'ml' },
        name: { az: 'İsti şokolad', ru: 'Горячий шоколад', en: 'Hot chocolate' },
        desc: {
          az: 'Süddə əridilmiş 70% qara şokolad. Qatıdır.',
          ru: 'Тёмный шоколад 70%, растопленный в молоке. Густой.',
          en: '70% dark chocolate melted into milk. Thick.',
        },
      },
      {
        id: 'd3', price: 3.50, img: 'images/tea.jpg',
        weight: { v: 500, u: 'ml' },
        name: { az: 'Çay', ru: 'Чай', en: 'Tea' },
        desc: {
          az: 'Dəmlənmiş, iki nəfərlik şüşə çaydanda.',
          ru: 'Заварной, в стеклянном чайнике на двоих.',
          en: 'Loose leaf, in a glass pot for two.',
        },
        mods: [{
          id: 'kind', type: 'single', required: true,
          title: { az: 'Növ', ru: 'Вид', en: 'Kind' },
          choices: [
            { price: 0, name: { az: 'Qara', ru: 'Чёрный', en: 'Black' } },
            { price: 0, name: { az: 'Yaşıl', ru: 'Зелёный', en: 'Green' } },
            { price: 0.80, name: { az: 'Çaytikanı', ru: 'Облепиховый', en: 'Sea buckthorn' } },
            { price: 0.80, name: { az: 'Zəncəfil-limon', ru: 'Имбирь-лимон', en: 'Ginger & lemon' } },
          ],
        }],
      },
      {
        id: 'd4', price: 5.00, img: 'images/lemonade.jpg',
        weight: { v: 400, u: 'ml' },
        name: { az: 'Ev limonadı', ru: 'Домашний лимонад', en: 'House lemonade' },
        desc: {
          az: 'Təzə nanə, laym və buzlu qazlı su.',
          ru: 'Свежая мята, лайм и газированная вода со льдом.',
          en: 'Fresh mint, lime and sparkling water over ice.',
        },
        mods: [{
          id: 'flavor', type: 'single', required: true,
          title: { az: 'Dad', ru: 'Вкус', en: 'Flavour' },
          choices: [
            { price: 0, name: { az: 'Mohito', ru: 'Мохито', en: 'Mojito' } },
            { price: 0, name: { az: 'Sitrus', ru: 'Цитрус', en: 'Citrus' } },
            { price: 0, name: { az: 'Tarxun', ru: 'Тархун', en: 'Tarragon' } },
          ],
        }],
      },
      {
        id: 'd5', price: 5.50, img: 'images/berry-lemonade.jpg',
        weight: { v: 400, u: 'ml' },
        name: { az: 'Giləmeyvə limonadı', ru: 'Ягодный лимонад', en: 'Berry lemonade' },
        desc: {
          az: 'Çiyələk, moruq və reyhan. Həddindən artıq şirin deyil.',
          ru: 'Клубника, малина и базилик. Не приторный.',
          en: 'Strawberry, raspberry and basil. Not too sweet.',
        },
      },
      {
        id: 'd6', price: 6.00, img: 'images/orange-juice.jpg',
        weight: { v: 300, u: 'ml' },
        name: { az: 'Portağal freşi', ru: 'Апельсиновый фреш', en: 'Fresh orange juice' },
        desc: {
          az: 'Stəkanda dörd portağal, sifarişdən sonra sıxırıq.',
          ru: 'Четыре апельсина в стакане, отжимаем после заказа.',
          en: 'Four oranges per glass, pressed after you order.',
        },
      },
      {
        id: 'd7', price: 2.50, img: 'images/cola.jpg',
        weight: { v: 400, u: 'ml' },
        name: { az: 'Kola', ru: 'Кола', en: 'Cola' },
        desc: {
          az: 'Buz və laym dilimi ilə.',
          ru: 'Со льдом и долькой лайма.',
          en: 'With ice and a wedge of lime.',
        },
      },
      {
        id: 'd8', price: 6.90, img: 'images/smoothie.jpg',
        weight: { v: 400, u: 'ml' },
        name: { az: 'Giləmeyvə smuzi', ru: 'Ягодный смузи', en: 'Berry smoothie' },
        desc: {
          az: 'Qaragilə, moruq, banan və yoqurt.',
          ru: 'Черника, малина, банан и йогурт.',
          en: 'Blueberry, raspberry, banana and yoghurt.',
        },
      },
      {
        id: 'd9', price: 6.50, img: 'images/milkshake.jpg',
        weight: { v: 400, u: 'ml' }, tag: 'hit',
        name: { az: 'Süd kokteyli', ru: 'Молочный коктейль', en: 'Milkshake' },
        desc: {
          az: 'Plombirdən, üstündə çalınmış qaymaq.',
          ru: 'На пломбире, взбитые сливки сверху.',
          en: 'Made with ice cream, whipped cream on top.',
        },
        mods: [{
          id: 'flavor', type: 'single', required: true,
          title: { az: 'Dad', ru: 'Вкус', en: 'Flavour' },
          choices: [
            { price: 0, name: { az: 'Şokolad', ru: 'Шоколад', en: 'Chocolate' } },
            { price: 0, name: { az: 'Vanil', ru: 'Ваниль', en: 'Vanilla' } },
            { price: 0, name: { az: 'Çiyələk', ru: 'Клубника', en: 'Strawberry' } },
            { price: 0.80, name: { az: 'Oreo', ru: 'Орео', en: 'Oreo' } },
          ],
        }],
      },
    ],
  },

  {
    id: 'desserts',
    title: { az: 'Desertlər', ru: 'Десерты', en: 'Desserts' },
    note: {
      az: 'Özümüzdə bişiririk, səhər gətiririk',
      ru: 'Печём у себя, привозим утром',
      en: 'Baked in-house, delivered each morning',
    },
    items: [
      {
        id: 's1', price: 6.50, img: 'images/cheesecake.jpg',
        weight: { v: 140, u: 'g' }, kcal: 390,
        name: { az: 'Nyu-York çizkeyki', ru: 'Чизкейк Нью-Йорк', en: 'New York cheesecake' },
        desc: {
          az: 'Sıx, qum əsasında. Klassik resept.',
          ru: 'Плотный, на песочной основе. Классический рецепт.',
          en: 'Dense, on a shortcrust base. The classic recipe.',
        },
      },
      {
        id: 's2', price: 6.90, img: 'images/cheesecake-berry.jpg',
        weight: { v: 150, u: 'g' }, kcal: 410,
        name: { az: 'Qaragilə çizkeyki', ru: 'Чизкейк с черникой', en: 'Blueberry cheesecake' },
        desc: {
          az: 'Eyni çizkeyk, amma qaragilə konfiturunun altında.',
          ru: 'Тот же чизкейк, но под черничным конфитюром.',
          en: 'The same cheesecake, under blueberry compote.',
        },
      },
      {
        id: 's3', price: 5.50, img: 'images/brownie.jpg',
        weight: { v: 120, u: 'g' }, kcal: 450, tag: 'hit',
        name: { az: 'Şokoladlı brauni', ru: 'Шоколадный брауни', en: 'Chocolate brownie' },
        desc: {
          az: 'İçi nəm, üstü qabıqlı. İsti halda daha dadlıdır.',
          ru: 'Влажный внутри, с корочкой сверху. Тёплым — вкуснее.',
          en: 'Fudgy inside, crisp on top. Better warm.',
        },
      },
      {
        id: 's4', price: 3.50, img: 'images/croissant.jpg',
        weight: { v: 90, u: 'g' }, kcal: 280,
        name: { az: 'Kruassan', ru: 'Круассан', en: 'Croissant' },
        desc: {
          az: 'Qatlı, kərə yağında. Səhər — hələ isti.',
          ru: 'Слоёный, на сливочном масле. Утром — ещё тёплый.',
          en: 'Flaky, all butter. Still warm in the morning.',
        },
      },
      {
        id: 's5', price: 7.50, img: 'images/pancakes.jpg',
        weight: { v: 260, u: 'g' }, kcal: 520,
        name: { az: 'Penkeyklər', ru: 'Панкейки', en: 'Pancakes' },
        desc: {
          az: 'Dörd ədəddən ibarət, ağcaqayın siropu və giləmeyvə ilə.',
          ru: 'Стопка из четырёх, с кленовым сиропом и ягодами.',
          en: 'A stack of four, with maple syrup and berries.',
        },
      },
    ],
  },
];

/* Отзывы-заглушки. Новые отзывы гостей сохраняются в браузере
   и одновременно уходят вам в WhatsApp. */
const SEED_REVIEWS = [
  {
    name: 'Aysel', rating: 5, date: '2026-08-24',
    text: {
      az: 'Kapuçino əladır, köpük sıxdır və dağılmır. Hər səhər işə gedərkən alıram.',
      ru: 'Капучино отличный, пенка плотная и не расслаивается. Беру каждое утро по дороге на работу.',
      en: 'Great cappuccino — dense foam that holds. I get one every morning on my way to work.',
    },
  },
  {
    name: 'Nihat', rating: 5, date: '2026-08-21',
    text: {
      az: 'Dabl Çizi masadan QR ilə sifariş etdim — 12 dəqiqəyə gətirdilər. Kotlet həqiqətən kömürdəndir.',
      ru: 'Заказал Дабл Чиз через QR прямо за столиком — принесли за 12 минут. Котлета реально с углей.',
      en: 'Ordered a Double Cheese by QR right at the table — arrived in 12 minutes. The patty really is charcoal-grilled.',
    },
  },
  {
    name: 'Elvin', rating: 4, date: '2026-08-19',
    text: {
      az: 'Trüfellı fri rayonda ən yaxşısıdır. Sadəcə «standart» porsiya azdır, böyüyü götürün.',
      ru: 'Фри с трюфелем — лучшее в районе. Единственное, порция «стандарт» маловата, берите большую.',
      en: 'Truffle fries are the best around. Only thing — the regular portion is small, order the large one.',
    },
  },
  {
    name: 'Leyla', rating: 5, date: '2026-08-15',
    text: {
      az: 'Yağışda gəldik, pled verdilər və kakao süzdülər. Xırda şeydir, amma yadda qaldı.',
      ru: 'Пришли в дождь, дали плед и налили какао. Мелочь, а запомнилось.',
      en: 'We came in out of the rain, they handed us a blanket and poured cocoa. A small thing, but it stuck.',
    },
  },
];
