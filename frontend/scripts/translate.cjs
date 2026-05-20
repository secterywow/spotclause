/**
 * Auto-translate script for SpotClause i18n.
 *
 * Usage:
 *   node scripts/translate.js
 *
 * Requires DEEPL_API_KEY env var for real translation.
 * Without it, missing keys are filled with English as placeholders.
 */

const fs = require('fs')
const path = require('path')

const LOCALES_DIR = path.join(__dirname, '..', 'src', 'locales')
const SOURCE_LANG = 'en'

// Target languages (excluding source)
const TARGET_LANGS = [
  'de', 'fr', 'es', 'pt', 'it', 'ar', 'tr', 'th',
  'ru', 'id', 'ja', 'ko', 'zh-TW'
]

const DEEPL_API_KEY = process.env.DEEPL_API_KEY
const DEEPL_API_URL = 'https://api-free.deepl.com/v2/translate'

async function translateWithDeepL(texts, targetLang) {
  if (!DEEPL_API_KEY || texts.length === 0) return texts

  // DeepL uses 'zh' for Chinese (not 'zh-TW')
  const deeplLang = targetLang === 'zh-TW' ? 'ZH' : targetLang.toUpperCase()

  const body = new URLSearchParams()
  texts.forEach(t => body.append('text', t))
  body.append('target_lang', deeplLang)
  body.append('source_lang', 'EN')

  try {
    const res = await fetch(DEEPL_API_URL, {
      method: 'POST',
      headers: { 'Authorization': `DeepL-Auth-Key ${DEEPL_API_KEY}` },
      body,
    })
    if (!res.ok) {
      const err = await res.text()
      console.error(`DeepL API error for ${targetLang}:`, err)
      return texts
    }
    const data = await res.json()
    return data.translations.map(t => t.text)
  } catch (e) {
    console.error(`DeepL request failed for ${targetLang}:`, e.message)
    return texts
  }
}

function flatten(obj, prefix = '') {
  const result = {}
  for (const [key, val] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (typeof val === 'object' && val !== null) {
      Object.assign(result, flatten(val, fullKey))
    } else {
      result[fullKey] = val
    }
  }
  return result
}

function unflatten(flat) {
  const result = {}
  for (const [key, val] of Object.entries(flat)) {
    const parts = key.split('.')
    let curr = result
    for (let i = 0; i < parts.length - 1; i++) {
      if (!curr[parts[i]]) curr[parts[i]] = {}
      curr = curr[parts[i]]
    }
    curr[parts[parts.length - 1]] = val
  }
  return result
}

async function processLang(lang) {
  const targetPath = path.join(LOCALES_DIR, `${lang}.json`)
  let target = {}
  try {
    target = JSON.parse(fs.readFileSync(targetPath, 'utf-8'))
  } catch {
    console.log(`  Creating new file: ${lang}.json`)
  }

  const sourceFlat = flatten(source)
  const targetFlat = flatten(target)

  const missingKeys = Object.keys(sourceFlat).filter(k => !(k in targetFlat))
  if (missingKeys.length === 0) {
    console.log(`  ${lang}: up to date`)
    return
  }

  console.log(`  ${lang}: ${missingKeys.length} missing keys`)

  // Collect texts to translate
  const textsToTranslate = missingKeys.map(k => sourceFlat[k])

  // Translate (or fallback to English)
  let translations
  if (DEEPL_API_KEY) {
    translations = await translateWithDeepL(textsToTranslate, lang)
  } else {
    translations = textsToTranslate
    console.log(`    → Using English placeholders (set DEEPL_API_KEY for real translation)`)
  }

  // Merge back
  for (let i = 0; i < missingKeys.length; i++) {
    targetFlat[missingKeys[i]] = translations[i]
  }

  // Write back with same key order as source
  const orderedFlat = {}
  for (const k of Object.keys(sourceFlat)) {
    orderedFlat[k] = targetFlat[k] !== undefined ? targetFlat[k] : sourceFlat[k]
  }

  const output = unflatten(orderedFlat)
  fs.writeFileSync(targetPath, JSON.stringify(output, null, 2) + '\n')
  console.log(`  ${lang}: saved`)
}

async function main() {
  const sourcePath = path.join(LOCALES_DIR, `${SOURCE_LANG}.json`)
  source = JSON.parse(fs.readFileSync(sourcePath, 'utf-8'))

  console.log('Source:', SOURCE_LANG)
  console.log('Targets:', TARGET_LANGS.join(', '))
  console.log('API key:', DEEPL_API_KEY ? 'yes' : 'no (English placeholders)')
  console.log('')

  for (const lang of TARGET_LANGS) {
    await processLang(lang)
  }

  console.log('\nDone.')
  if (!DEEPL_API_KEY) {
    console.log('\nTo translate with DeepL:')
    console.log('  1. Get a free API key at https://www.deepl.com/pro-api')
    console.log('  2. Run: DEEPL_API_KEY=xxx node scripts/translate.js')
  }
}

let source
main().catch(console.error)
