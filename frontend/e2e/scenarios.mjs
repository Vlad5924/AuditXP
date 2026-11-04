// Сценарные тесты интерфейса AuditXP (Playwright)
// Запуск при работающем сервере с демо-базой
//   node e2e/scenarios.mjs http://127.0.0.1:8000/
// Движок браузера задается переменной BROWSER (chromium, firefox, webkit)
import { chromium, firefox, webkit } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000/";
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SAMPLE = path.join(ROOT, "samples", "erp_export_2026-11-01_2026-11-03.csv");
const results = [];

function check(condition, message) {
  if (!condition) throw new Error(message);
}

async function login(page, user, password) {
  await page.goto(BASE + "#/overview");
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.reload();
  await page.fill("input[autocomplete=username]", user);
  await page.fill("input[type=password]", password);
  await page.getByRole("button", { name: "Войти" }).click();
}

async function scenario(id, title, page, body) {
  const started = Date.now();
  try {
    await body(page);
    results.push({ id, title, ok: true, ms: Date.now() - started });
  } catch (error) {
    results.push({ id, title, ok: false, ms: Date.now() - started,
      error: error.message.split("\n")[0] });
  }
}

const ENGINE = process.env.BROWSER ?? "chromium";
const engines = { chromium, firefox, webkit };
const browser = await engines[ENGINE].launch(ENGINE === "chromium"
  ? { executablePath: process.env.CHROMIUM_PATH || undefined,
      args: ["--lang=ru-RU"] }
  : {});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 },
  locale: "ru-RU" });
const page = await context.newPage();
page.setDefaultTimeout(15000);

await scenario("E2E-01", "Вход аудитора и показатели обзора", page, async (p) => {
  await login(p, "zhdanko", "Auditor2026");
  await p.waitForSelector("text=Обзор рисков");
  check(await p.locator(".kpi-row .kpi, .kpi").count() >= 4, "нет плиток KPI");
});

await scenario("E2E-02", "Неверный пароль и остаток попыток", page, async (p) => {
  await login(p, "litvinova", "Wrong2026");
  const alert = p.locator(".alert.danger");
  await alert.waitFor();
  check((await alert.innerText()).includes("осталось попыток 4"),
    "нет сообщения об остатке попыток");
});

await scenario("E2E-03", "Восстановление пароля без раскрытия адреса", page, async (p) => {
  await p.getByRole("button", { name: "Забыли пароль?" }).click();
  await p.fill("input[type=email]", "nobody@goldberg-soft.by");
  await p.getByRole("button", { name: "Отправить ссылку" }).click();
  const info = p.locator(".alert.success");
  await info.waitFor();
  check((await info.innerText()).startsWith("Если адрес зарегистрирован"),
    "сообщение раскрывает наличие адреса");
});

await scenario("E2E-04", "Фильтр реестра по состоянию «Оценен»", page, async (p) => {
  await login(p, "zhdanko", "Auditor2026");
  await p.waitForSelector("text=Обзор рисков");
  await p.goto(BASE + "#/risks");
  await p.waitForSelector("table.table tbody tr");
  await p.locator(".filters select").first().selectOption("Оценен");
  await p.waitForTimeout(800);
  const states = await p.locator("table.table tbody tr td:last-child").allInnerTexts();
  check(states.length > 0 && states.every((s) => s.trim() === "Оценен"),
    "в выборке есть риски в других состояниях");
});

await scenario("E2E-05", "Обработка риска без закрытия карточки", page, async (p) => {
  await p.locator("table.table tbody tr").first().click();
  const drawer = p.locator("aside.drawer");
  await drawer.getByRole("button", { name: "Подтвердить" }).click();
  await drawer.getByRole("button", { name: "Назначить мероприятие" }).click();
  await p.locator(".modal textarea").fill("Сверка расчетов с контрагентом");
  await p.locator(".modal input:not([type=date])").fill("Литвинова Е.С.");
  await p.locator(".modal input[type=date]").fill("2026-11-20");
  await p.locator(".modal").getByRole("button", { name: "Назначить мероприятие" }).click();
  await drawer.locator("text=В проработке").first().waitFor();
  check(await drawer.getByRole("button", { name: "Выполнить мероприятие" }).count() === 1,
    "нет действия «Выполнить мероприятие»");
});

await scenario("E2E-06", "Импорт файла CSV со скорингом периода файла", page, async (p) => {
  await p.goto(BASE + "#/import");
  await p.locator(".source-choice label").nth(1).click();
  await p.setInputFiles("input[type=file]", SAMPLE);
  await p.getByRole("button", { name: "Далее" }).click();
  await p.waitForSelector("text=Внимание");
  check(await p.locator("text=Не сопоставлено").count() === 1, "нет статуса пропуска");
  await p.getByRole("button", { name: "Далее" }).click();
  await p.getByRole("button", { name: "Далее" }).click();
  await p.getByRole("button", { name: "Загрузить данные" }).click();
  const done = p.locator(".wizard .alert.success");
  await done.waitFor({ timeout: 60000 });
  const created = Number((await done.innerText()).match(/новых рисков\s+(\d+)/)[1]);
  check(created > 0, "скоринг не создал рисков за период файла");
  const period = await p.locator("table.table tbody tr").first().locator("td").nth(2).innerText();
  check(period.includes("01.11.2026"), "в журнале не указан период файла");
});

await scenario("E2E-07", "Утверждение отчета руководителем с ЭЦП", page, async (p) => {
  await login(p, "kovalchuk", "Chief2026");
  await p.waitForSelector("text=Обзор рисков");
  await p.goto(BASE + "#/reports");
  await p.locator("button", { hasText: "10.2026" }).first().click();
  await p.getByRole("button", { name: "Утвердить" }).click();
  await p.getByRole("button", { name: "Проверить подпись" }).click();
  await p.locator("text=подпись действительна").waitFor();
});

await scenario("E2E-08", "Разграничение вкладок по ролям", page, async (p) => {
  await login(p, "admin", "Admin2026");
  await p.waitForSelector("header");
  const tabs = await p.locator("header nav button, header nav a").allInnerTexts();
  check(tabs.includes("Пользователи") && !tabs.includes("Импорт"),
    "набор вкладок не соответствует роли " + tabs.join(","));
});

await scenario("E2E-09", "Экраны без прокрутки по ширине при 1366×768", page, async (p) => {
  await login(p, "kovalchuk", "Chief2026");
  await p.waitForSelector("text=Обзор рисков");
  await p.setViewportSize({ width: 1366, height: 768 });
  const wide = [];
  for (const route of ["overview", "risks", "heatmap", "import", "reports", "audit"]) {
    await p.goto(BASE + "#/" + route);
    await p.waitForTimeout(900);
    const overflow = await p.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 0) wide.push(`${route} +${overflow}px`);
  }
  check(wide.length === 0, "горизонтальная прокрутка " + wide.join(", "));
});

await page.close();
await browser.close();
for (const r of results) {
  console.log(`${r.ok ? "PASS" : "FAIL"} ${r.id} ${r.title} (${(r.ms / 1000).toFixed(1)} с)` +
    (r.ok ? "" : ` – ${r.error}`));
}
const failed = results.filter((r) => !r.ok).length;
console.log(`Итого ${results.length}, успешно ${results.length - failed}, ошибок ${failed}`);
process.exit(failed ? 1 : 0);
