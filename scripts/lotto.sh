#!/usr/bin/env bash
# Un giro completo di un lotto di traduzione (missioni, dialoghi dei PNG, obiettivi e testi d'area;
# docs/content/translation-style-guide.md).
#
#   scripts/lotto.sh taglia <kind> <nome> <ids-file|-> <size>
#       → pipeline/batches/<nome>.<kind>.jsonl (translate_batch cut --ids), stampa quante righe.
#         <ids-file>: un id per riga (`#` commenta; id di missione, hash del testo per gossip, id numerico
#         per objective e area); `-` al posto del file = nessun filtro: tutte le righe non ancora tradotte,
#         fino a <size>. <kind>: quest_title, quest_objectives, quest_description, progress, completion,
#         gossip, objective, area, book.
#   scripts/lotto.sh importa <nome>
#       → per ogni pipeline/batches/<nome>.<kind>.draft.jsonl (righe {"ref","it"}) translate_lint; se anche una
#         sola bozza ha un errore (ref mancante, duplicato, nome del glossario, segnaposto…) si ferma prima di
#         importare. Poi translate_batch expand --name <nome>-sg<N>, wfj import draft (machine, MODEL,
#         data di oggi), translate_batch keep (le righe {"ref","it":null}, che restano in inglese, in
#         pipeline/keep_english.tsv: non vengono importate né ritagliate), wfj check (che non deve far crescere
#         le righe respinte né i duplicate_conflict: una bozza che dà un altro italiano a righe già tradotte da un
#         altro lotto viene rifiutata), wfj generate e il rapporto
#         di copertura (come `make coverage`: docs/operations/coverage.md e i conteggi in README.md e
#         docs/curseforge.md, così ogni import lascia i documenti generati aggiornati). Se un passo fallisce,
#         data/, l'addon, pipeline/keep_english.tsv e quei documenti tornano come prima.
#
# Variabili: LOTTO_ROOT (il repo con data/, default questo), PY (python), LOTTO_MODEL (default
# claude-opus-5-5), LOTTO_DATE (default oggi).
set -euo pipefail

CODE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "${LOTTO_ROOT:-$CODE}" && pwd)"
if [ -z "${PY:-}" ]; then
	common="$(git -C "$CODE" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
	venv="${common:+$(dirname "$common")/.venv/bin/python}"
	if [ -n "$venv" ] && [ -x "$venv" ]; then PY="$venv"; else PY=python3; fi
fi
MODEL="${LOTTO_MODEL:-claude-opus-5-5}"
DATE="${LOTTO_DATE:-$(date +%F)}"
BATCHES="$ROOT/pipeline/batches"
export PYTHONPATH="$CODE/pipeline${PYTHONPATH:+:$PYTHONPATH}"
KINDS="quest_title quest_objectives quest_description progress completion gossip objective area book item_description spell_description spell_aura"

usage() {
	echo "uso: scripts/lotto.sh taglia <kind> <nome> <ids-file|-> <size> | importa <nome>" >&2
	exit 2
}

wfj() { (cd "$ROOT" && "$PY" -m "$@"); }

taglia() {
	[ $# -eq 4 ] || usage
	local kind="$1" nome="$2" ids="$3" size="$4"
	case " $KINDS " in *" $kind "*) ;; *) echo "lotto: kind $kind non è uno di: $KINDS" >&2; exit 2;; esac
	local idargs=()
	if [ "$ids" != - ]; then
		[ -f "$ids" ] || { echo "lotto: nessun file di id $ids" >&2; exit 1; }
		ids="$(cd "$(dirname "$ids")" && pwd)/$(basename "$ids")"
		idargs=(--ids "$ids")
	fi
	mkdir -p "$BATCHES"
	local out="$BATCHES/$nome.$kind.jsonl"
	wfj wfj.dev.translate_batch cut --kind "$kind" --size "$size" ${idargs[@]+"${idargs[@]}"} --out "$out"
	echo "lotto: $(grep -c . "$out" || true) righe → pipeline/batches/$nome.$kind.jsonl"
}

importa() {
	[ $# -eq 1 ] || usage
	local nome="$1" version
	version="$(sed -n 's/^version: sg\([0-9][0-9]*\)$/\1/p' "$ROOT/docs/content/translation-style-guide.md" | head -1)"
	[ -n "$version" ] || { echo "lotto: la guida di stile non dichiara 'version: sgN'" >&2; exit 1; }
	local name="$nome-sg$version"
	shopt -s nullglob
	local drafts=("$BATCHES/$nome".*.draft.jsonl)
	shopt -u nullglob
	[ ${#drafts[@]} -gt 0 ] || { echo "lotto: nessuna bozza pipeline/batches/$nome.<kind>.draft.jsonl" >&2; exit 1; }

	# 1. ogni bozza contro il suo lotto: tutte prima di toccare qualcosa
	local failed=0 oks=() keeps=() draft batch
	for draft in "${drafts[@]}"; do
		batch="${draft%.draft.jsonl}.jsonl"
		if [ ! -f "$batch" ]; then
			echo "lotto: $(basename "$draft") non ha il lotto $(basename "$batch")" >&2
			failed=1
			continue
		fi
		echo "lotto: lint $(basename "$draft")"
		wfj wfj.dev.translate_lint "$batch" "$draft" || failed=1
		oks+=("${draft%.jsonl}.ok.jsonl")
		keeps+=("${draft%.jsonl}.keep.jsonl")
	done
	if [ "$failed" -ne 0 ]; then
		echo "lotto: bozze con errori, niente importato (data/ invariato)" >&2
		exit 1
	fi

	# 2. le righe buone di tutti i kind → un file di import per tipo
	local work="$BATCHES/$nome.import"
	rm -rf "$work"
	mkdir -p "$work"
	cat "${oks[@]}" > "$work/$nome.ok.jsonl"
	wfj wfj.dev.translate_batch expand "$work/$nome.ok.jsonl" --name "$name" --out "$work"

	# 3. import, check, generate, copertura: al primo errore data/, l'addon e i documenti tornano come prima.
	# Le righe respinte (e quelle in duplicate_conflict) non devono crescere: i conflitti già presenti non
	# bloccano un lotto che non ne aggiunge.
	local rej_before rej_after
	rej_before="$(wfj wfj.dev.translate_batch rejected)"
	local snap
	snap="$(mktemp -d)"
	cp -a "$ROOT/data" "$snap/data"
	cp -a "$ROOT/addon" "$snap/addon"
	local keep="$ROOT/pipeline/keep_english.tsv"
	[ ! -f "$keep" ] || cp -a "$keep" "$snap/keep_english.tsv"
	local docs=(README.md docs/curseforge.md docs/operations/coverage.md) doc
	for doc in "${docs[@]}"; do
		[ ! -f "$ROOT/$doc" ] || { mkdir -p "$snap/docs/$(dirname "$doc")"; cp -a "$ROOT/$doc" "$snap/docs/$doc"; }
	done
	restore() {
		echo "lotto: errore, ripristino data/, addon/, pipeline/keep_english.tsv e i documenti generati" >&2
		rm -rf "$ROOT/data" "$ROOT/addon"
		cp -a "$snap/data" "$ROOT/data"
		cp -a "$snap/addon" "$ROOT/addon"
		if [ -f "$snap/keep_english.tsv" ]; then cp -a "$snap/keep_english.tsv" "$keep"; else rm -f "$keep"; fi
		for doc in "${docs[@]}"; do
			if [ -f "$snap/docs/$doc" ]; then cp -a "$snap/docs/$doc" "$ROOT/$doc"; else rm -f "$ROOT/$doc"; fi
		done
		rm -rf "$snap"
		exit 1
	}
	local file type
	shopt -s nullglob
	local imports=("$work/$name".*.jsonl)
	shopt -u nullglob
	for file in "${imports[@]}"; do
		type="${file#"$work/$name."}"
		type="${type%.jsonl}"
		wfj wfj import draft "$type" "$file" --model "$MODEL" --date "$DATE" --name "$name" || restore
	done
	wfj wfj.dev.translate_batch keep "${keeps[@]}" || restore
	wfj wfj check --report || restore
	rej_after="$(wfj wfj.dev.translate_batch rejected)" || restore
	if [ "${rej_after% *}" -gt "${rej_before% *}" ] || [ "${rej_after#* }" -gt "${rej_before#* }" ]; then
		echo "lotto: righe respinte ${rej_before% *} → ${rej_after% *}, duplicate_conflict ${rej_before#* } → ${rej_after#* }: la bozza dà un italiano diverso a righe già tradotte" >&2
		restore
	fi
	wfj wfj generate || restore
	# il rapporto di copertura e i conteggi, come `make coverage` (con la build fissata nel Makefile)
	local build
	build="$(sed -n 's/^forever_BUILD[[:space:]]*:=[[:space:]]*//p' "$CODE/Makefile" | head -1)"
	wfj wfj.dev.coverage --out "$ROOT/docs/operations/coverage.md" ${build:+--build "$build"} || restore
	rm -rf "$snap"
	echo "lotto: $nome importato come $name@$DATE"
}

[ $# -ge 1 ] || usage
cmd="$1"
shift
case "$cmd" in
	taglia) taglia "$@" ;;
	importa) importa "$@" ;;
	*) usage ;;
esac
