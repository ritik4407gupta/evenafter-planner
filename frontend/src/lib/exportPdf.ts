/** Dependency-free PDF export for the event workspace and generated plans. */
export type PdfSection = { heading: string; lines: string[] }

function plainAscii(value: string): string {
  return value
    .replace(/₹/g, 'INR ')
    .replace(/[•·]/g, '-')
    .replace(/[–—]/g, '-')
    .replace(/[“”]/g, '"')
    .replace(/[’‘]/g, "'")
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\x20-\x7E]/g, '')
}

function wrapLine(value: string, width = 88): string[] {
  const clean = plainAscii(value).trim()
  if (!clean) return ['']
  const words = clean.split(/\s+/)
  const lines: string[] = []
  let current = ''
  for (const word of words) {
    if (!current) current = word
    else if (`${current} ${word}`.length <= width) current += ` ${word}`
    else { lines.push(current); current = word }
  }
  if (current) lines.push(current)
  return lines
}

function escapePdf(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
}

export function downloadPlanPdf(filename: string, title: string, sections: PdfSection[]) {
  const pageLines: string[][] = []
  let lines: string[] = [plainAscii(title), `Prepared by EverAfter | ${new Date().toLocaleDateString('en-IN')}`, '']
  const pushLine = (line: string) => {
    lines.push(...wrapLine(line))
    if (lines.length >= 49) { pageLines.push(lines); lines = [] }
  }
  for (const section of sections) {
    if (lines.length > 43) { pageLines.push(lines); lines = [] }
    pushLine(section.heading.toUpperCase())
    pushLine('-'.repeat(Math.min(42, section.heading.length + 5)))
    for (const line of section.lines) pushLine(line)
    pushLine('')
  }
  if (lines.length) pageLines.push(lines)
  if (!pageLines.length) pageLines.push([plainAscii(title)])

  const objects: string[] = []
  const pageIds = pageLines.map((_, i) => 4 + i * 2)
  objects[1] = '<< /Type /Catalog /Pages 2 0 R >>'
  objects[2] = `<< /Type /Pages /Kids [${pageIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pageIds.length} >>`
  objects[3] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
  pageLines.forEach((page, i) => {
    const pageId = pageIds[i]
    const contentId = pageId + 1
    const drawing = [
      'BT', '/F1 10 Tf', '48 792 Td', '14 TL',
      ...page.flatMap((line, index) => index === 0 ? [`/F1 17 Tf (${escapePdf(line)}) Tj`, '/F1 10 Tf', '0 -25 Td'] : [`(${escapePdf(line)}) Tj`, 'T*']),
      'ET',
    ].join('\n')
    objects[pageId] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentId} 0 R >>`
    objects[contentId] = `<< /Length ${drawing.length} >>\nstream\n${drawing}\nendstream`
  })

  let output = '%PDF-1.4\n%EVERAFTER\n'
  const offsets: number[] = [0]
  for (let id = 1; id < objects.length; id++) {
    offsets[id] = output.length
    output += `${id} 0 obj\n${objects[id]}\nendobj\n`
  }
  const xrefOffset = output.length
  output += `xref\n0 ${objects.length}\n0000000000 65535 f \n`
  for (let id = 1; id < objects.length; id++) output += `${String(offsets[id]).padStart(10, '0')} 00000 n \n`
  output += `trailer\n<< /Size ${objects.length} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`

  const blob = new Blob([output], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename.toLowerCase().endsWith('.pdf') ? filename : `${filename}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
