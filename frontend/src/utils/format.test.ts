import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatScore, initials, monthPeriod }
  from "./format";
import { zoneForScore } from "./risk";
import { duplicatedTargets, fieldState, missingRequired, toPayload }
  from "../hooks/mapping";

describe("форматирование", () => {
  it("UI-01 сумма с разделителем разрядов и запятой", () => {
    expect(formatMoney(1850000)).toBe("1 850 000,00 BYN");
    expect(formatMoney(4200000, true)).toBe("4,2 млн BYN");
  });
  it("UI-02 оценка с запятой и дата", () => {
    expect(formatScore(0.87)).toBe("0,87");
    expect(formatDate("2026-10-31")).toBe("31.10.2026");
  });
  it("UI-03 границы месяца и инициалы", () => {
    expect(monthPeriod(2026, 2)).toEqual({ date_from: "2026-02-01",
      date_to: "2026-02-28" });
    expect(initials("Жданько В.И.")).toBe("ВЖ");
  });
});

describe("зоны тепловой карты", () => {
  it("UI-04 пороги 5, 10 и 15 баллов", () => {
    expect([4, 5, 10, 15, 25].map(zoneForScore))
      .toEqual(["green", "yellow", "orange", "red", "red"]);
  });
});

describe("маппинг полей", () => {
  const full = { "Номер": "doc_number", "Дата": "transaction_date",
    "Сумма": "amount", "Контрагент": "counterparty_info",
    "Подразделение": "department", "Комментарий": null };
  it("UI-05 обязательные поля сопоставлены", () => {
    expect(missingRequired(full)).toEqual([]);
    expect(missingRequired({ ...full, "Сумма": null })).toEqual(["amount"]);
  });
  it("UI-06 повтор целевого поля дает предупреждение", () => {
    const twice = { ...full, "Комментарий": "amount" };
    expect(duplicatedTargets(twice)).toEqual(["amount"]);
    expect(fieldState(twice, "Сумма", "ok")).toBe("warning");
    expect(fieldState(full, "Комментарий", "missing")).toBe("missing");
  });
  it("UI-07 несопоставленные столбцы не передаются", () => {
    expect(Object.keys(toPayload(full))).not.toContain("Комментарий");
  });
});
