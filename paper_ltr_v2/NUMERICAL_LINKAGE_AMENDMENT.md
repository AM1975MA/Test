# Chiusura numerica prima dei fit V2 — 14 ottobre2026

Il preflight38562284435 ha verificato i90 checkpoint senza fit, poi ha bloccato
la ricostruzione bit-identica delle feature sotto il profilo CPU dei modelli.
La diagnosi38563762311 ha confrontato due profili sullo stesso host: per r3,
profilo corrente non esatto e storico con AVX512 esatto su125 feature, label,
chiavi e date. Su r1/r2 gli host non espongono AVX512 e nessuno dei due profili
ricostruisce esattamente le feature. I ranghi e le maschere restano identici;
non vengono tuttavia usati come sostituto del confronto esatto.

Il produttore TI originale usava NumPy2.3.5/Pandas2.2.3, dispatchCPU predefinito
e2 thread; il fit ListNet usava profilo Haswell/AVX512 disabilitato e1 thread.
Sono due contratti distinti: i fit consumano il TI congelato, non lo ricostruiscono.

Decisione: certificare tutti i tre TI in un job compatibile con il profilo
storico e riusare la chiusura mediante hash. Verificare AVX512 prima di
download/installazione; se l'host assegnato non è compatibile, massimo6 tentativi
di acquisizione di host, senza fit o ricerca di performance. Il gate rimane
esatto, nessuna tolleranza, quantizzazione o sostituzione delle feature.

I nuovi fit manterranno il profilo numerico del fit V1, i TI originali e le
ricette preregistrate. L'audit dei90 checkpoint già concluso viene conservato
come artefatto11892402901, senza ripetere l'addestramento né la sua diagnosi.
Questa precisazione riguarda solo la certificazione di provenienza; nessun
risultato BUDGET300 o LINEAR era disponibile al momento della decisione.
