// Input-only kg validation/visual balance. Never calculates money, ledger stock or allocation.
export function micro(value: string): bigint | null {
  const v = value.trim().replace(",", ".");
  if (!/^(0|[1-9]\d{0,11})(\.\d{1,6})?$/.test(v)) return null;
  const [w, f = ""] = v.split(".");
  return BigInt(w) * 1000000n + BigInt(f.padEnd(6, "0"));
}
export function kg(value: bigint) {
  return `${value / 1000000n}.${(value % 1000000n).toString().padStart(6, "0")}`;
}
export function balance(
  input: string,
  outputs: string[],
  differences: string[],
) {
  const source = micro(input),
    out = outputs.map(micro),
    diff = differences.map(micro);
  if (
    source === null ||
    out.some((x) => x === null) ||
    diff.some((x) => x === null)
  )
    return null;
  const sum = (v: Array<bigint | null>) =>
    v.reduce<bigint>((a, b) => a + (b ?? 0n), 0n);
  return {
    input: kg(source),
    output: kg(sum(out)),
    difference: kg(sum(diff)),
    balanced: source === sum(out) + sum(diff),
  };
}
