#!/usr/bin/env python3
"""
Gera o index.html do dashboard Monet a partir de um dataset exportado do Notion.

Uso:
    python3 generate_dashboard.py dataset.json alertas.json TEMPLATE.html > index.html

dataset.json: lista de registros da base "Carteira de ECs — Monet" (ver monet_sync_query.md)
alertas.json: lista de registros da base "🚨 Alertas & Pedidos da Diretoria" (não resolvidos)
TEMPLATE.html: o index.html anterior (usado como base para preservar CSS/estrutura/funções
               que não mudam a cada sync — o script SUBSTITUI apenas os trechos necessários)
"""
import sys, json, re, unicodedata
from datetime import date, datetime

ETAPAS = [
    ("Prospecção", "#8B92A8"),
    ("Negociação", "#FBBF24"),
    ("Fechamento", "#FB923C"),
    ("Aguardando Conta Monet", "#60A5FA"),
    ("Erro — Pendência FiServ", "#DE8FBF"),
    ("Erro — Pendência Monet", "#C9A84C"),
    ("Em Análise (Crédito e Risco)", "#A78BFA"),
    ("Aceito — Ativo com POS", "#4ADE80"),
    ("Aceito — NÃO Ativo com POS", "#5DCAA5"),
    ("Aceito — Ativo E sem POS", "#2DD4BF"),
    ("Recusado", "#F87171"),
    ("Cancelado", "#DC2626"),
]
ETAPA_SHORT = {
    "Prospecção": "Prospecção", "Negociação": "Negociação", "Fechamento": "Fechamento",
    "Aguardando Conta Monet": "Aguard. conta", "Erro — Pendência FiServ": "Erro FiServ",
    "Erro — Pendência Monet": "Erro Monet", "Em Análise (Crédito e Risco)": "Em análise",
    "Aceito — Ativo com POS": "Ativo c/ POS", "Aceito — NÃO Ativo com POS": "POS entregue",
    "Aceito — Ativo E sem POS": "Ativo s/ POS", "Recusado": "Recusado", "Cancelado": "Cancelado",
}
CONSULTORES = ["Durval","Neto","Antônio","Giovanna","Ilma","Allan","Gabriela","Franciele",
               "Jhennifer","Lania","Júlio","Letícia","Mateus","Sammya","Bárbara"]
CONS_COLORS = ["#C9A84C","#2DD4BF","#60A5FA","#A78BFA","#4ADE80","#FBBF24","#F87171",
               "#E8C870","#5DCAA5","#DE8FBF","#FB923C","#94A3B8","#F472B6","#818CF8","#34D399"]

def norm(s):
    if not s: return ''
    s = s.upper()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]+', ' ', s).strip()

def iso_to_br(iso):
    if not iso: return ''
    try:
        d = datetime.strptime(iso[:10], '%Y-%m-%d')
        return d.strftime('%d/%m/%Y')
    except Exception:
        return ''

def doc_type(cpf_cnpj):
    if not cpf_cnpj: return ''
    digits = re.sub(r'\D', '', cpf_cnpj)
    if len(digits) >= 14: return 'CNPJ'
    if len(digits) >= 11: return 'CPF'
    return ''

def build_ecs_prosp(records):
    ecs, prosp = [], []
    for i, r in enumerate(records):
        estab = r.get('Estabelecimento')
        if not estab:
            continue
        etapa = r.get('Etapa') or 'Prospecção'
        consultor = r.get('Consultor')
        # Meta TPV no Notion e digitado em milhares (ex: 125 = R$125 mil) - converter p/ reais
        meta = (r.get('Meta TPV') or 0) * 1000
        d_br = iso_to_br(r.get('data_cad'))
        pos_pl = r.get('Situação POS (planilha)') or ''
        status_pl = r.get('Status Original (planilha)') or ''
        tipo = doc_type(r.get('CNPJ/CPF'))
        nicho = r.get('Segmento / Nicho') or r.get('SegmentoBackfill') or 'Não categorizado'
        row = {
            "c": i + 1, "e": estab, "k": consultor, "ko": consultor, "kn": consultor,
            "kf": consultor, "m": meta, "p": pos_pl, "d": d_br, "s": status_pl,
            "t": tipo, "n": nicho, "g": etapa,
        }
        ecs.append(row)
        if etapa == 'Prospecção':
            cat = r.get('Categoria de Prospecção') or r.get('CategoriaBackfill') or 'Não categorizado'
            prosp.append({
                "d": d_br, "k": consultor or 'Não atribuído', "e": estab,
                "f": r.get('Telefone') or '', "v": r.get('Observação') or status_pl or '',
                "c": r.get('Código Planilha') and 'Não informado' or 'Não informado',
                "cat": cat,
            })
    return ecs, prosp

def build_situacao_html(ecs, alertas, sync_ts):
    def cards(rows, color_var, render):
        if not rows:
            return '<div style="color:var(--text3);font-size:12px;padding:4px 0">Nenhum registro no momento.</div>'
        items = ''.join(render(r) for r in rows)
        return '<div style="margin-top:7px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px">' + items + '</div>'

    recusados = [r for r in ecs if r['g'] == 'Recusado']
    erros_fiserv = [r for r in ecs if r['g'] == 'Erro — Pendência FiServ']
    erros_monet = [r for r in ecs if r['g'] == 'Erro — Pendência Monet']
    analise = [r for r in ecs if r['g'] == 'Em Análise (Crédito e Risco)']

    def card(r, color, extra=''):
        return (f'<div style="background:var(--{color}-dim);border:1px solid rgba(0,0,0,.1);'
                f'border-radius:8px;padding:10px 14px;font-size:12px"><strong>{r["e"]}</strong> '
                f'<span style="color:var(--text3)">({r["k"] or "sem consultor"})</span><br/>'
                f'<span style="color:var(--text2)">{r["s"] or r["p"] or "—"}{extra}</span></div>')

    html = '<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.06em">1. Cadastros recusados pela FiServ — ' + str(len(recusados)) + ' EC(s)</div>'
    html += cards(recusados, 'red', lambda r: card(r, 'red'))

    html += '<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--purple);text-transform:uppercase;letter-spacing:.06em">2. Pendências com a FiServ — ' + str(len(erros_fiserv)) + ' EC(s)</div>'
    html += cards(erros_fiserv, 'purple', lambda r: card(r, 'purple'))

    html += '<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--amber);text-transform:uppercase;letter-spacing:.06em">3. Correções pendentes do lado Monet — ' + str(len(erros_monet)) + ' EC(s)</div>'
    html += cards(erros_monet, 'amber', lambda r: card(r, 'amber'))

    html += '<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--teal);text-transform:uppercase;letter-spacing:.06em">4. Em análise de crédito e risco — ' + str(len(analise)) + ' EC(s)</div>'
    html += cards(analise, 'teal', lambda r: card(r, 'teal'))

    # Alertas cadastrados manualmente pelo time (base "🚨 Alertas & Pedidos da Diretoria")
    if alertas:
        cat_groups = {}
        for a in alertas:
            cat_groups.setdefault(a.get('Categoria') or 'Outro', []).append(a)
        idx = 5
        for cat_name, rows in cat_groups.items():
            html += f'<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--gold2);text-transform:uppercase;letter-spacing:.06em">{idx}. {cat_name} — {len(rows)} item(ns)</div>'
            items = ''.join(
                f'<div style="background:var(--bg2);border-radius:8px;padding:10px 14px;font-size:12px">'
                f'<strong>{a.get("Estabelecimento / Assunto","")}</strong> '
                f'<span style="color:var(--text3)">({a.get("Consultor") or "—"}'
                + (f' · {a.get("Prioridade")}' if a.get("Prioridade") else '') + ')</span><br/>'
                f'<span style="color:var(--text2)">{a.get("Descrição") or ""}</span></div>'
                for a in rows
            )
            html += f'<div style="margin-top:7px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:8px">{items}</div>'
            idx += 1
    else:
        html += ('<div style="margin-top:14px;font-size:11px;font-weight:700;color:var(--gold2);text-transform:uppercase;letter-spacing:.06em">5. Alertas e pedidos comerciais do time</div>'
                  '<div style="margin-top:7px;font-size:12px;color:var(--text3)">Nenhum alerta registrado na base '
                  '"🚨 Alertas &amp; Pedidos da Diretoria" no Notion. Peça ao time para registrar lá os casos que '
                  'precisam aparecer aqui (risco de cancelamento, equipamento pendente, pedido comercial, etc).</div>')

    html += f'<div style="margin-top:16px;font-size:10px;color:var(--text3)">Sincronizado automaticamente do Notion em {sync_ts}. Itens 1–4 são calculados a partir da Etapa de cada EC; item 5 vem da base de Alertas — mantenha-a atualizada para que apareça aqui.</div>'
    return html


def main():
    dataset_path, alertas_path, template_path = sys.argv[1], sys.argv[2], sys.argv[3]
    records = json.load(open(dataset_path, encoding='utf-8'))
    alertas = json.load(open(alertas_path, encoding='utf-8')) if alertas_path != '-' else []
    html = open(template_path, encoding='utf-8').read()

    ecs, prosp = build_ecs_prosp(records)
    sync_ts = datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')

    # 1) ECS / PROSP arrays
    ecs_json = json.dumps(ecs, ensure_ascii=False)
    prosp_json = json.dumps(prosp, ensure_ascii=False)
    html = re.sub(r'const ECS = \[.*?\];\n', 'const ECS = ' + ecs_json + ';\n', html, count=1, flags=re.S)
    html = re.sub(r'const PROSP = \[.*?\];\n', 'const PROSP = ' + prosp_json + ';\n', html, count=1, flags=re.S)

    # 2) GRUPOS
    grupos_js = 'const GRUPOS=[\n' + '\n'.join(
        f"  {{key:{json.dumps(k, ensure_ascii=False)},label:{json.dumps(ETAPA_SHORT[k], ensure_ascii=False)},color:'{c}',hex:'{c}'}},"
        for k, c in ETAPAS
    ) + '\n];'
    html = re.sub(r'const GRUPOS=\[.*?\];', grupos_js, html, count=1, flags=re.S)

    # 3) KPI leaf-etapa checks
    html = html.replace("r.g==='POS entregue'", "r.g==='Aceito — Ativo com POS'")
    html = html.replace("r.g==='Em aprovação'", "r.g==='Em Análise (Crédito e Risco)'")

    # 4) grupoBadge map/short
    map_js = "{" + ",".join(f"{json.dumps(k, ensure_ascii=False)}:'b-gray'" for k, _ in ETAPAS) + "}"
    short_js = "{" + ",".join(f"{json.dumps(k, ensure_ascii=False)}:{json.dumps(ETAPA_SHORT[k], ensure_ascii=False)}" for k, _ in ETAPAS) + "}"
    html = re.sub(
        r"function grupoBadge\(g\)\{.*?\}\n",
        "function grupoBadge(g){const map=" + map_js + ";const short=" + short_js + ";"
        "return'<span class=\"badge '+(map[g]||'b-gray')+'\">'+(short[g]||g)+'</span>';}\n",
        html, count=1, flags=re.S,
    )

    # 5) ccol / deslig
    ccol_js = "const ccol={" + ",".join(f'"{n}":"{CONS_COLORS[i % len(CONS_COLORS)]}"' for i, n in enumerate(CONSULTORES)) + "};"
    html = re.sub(r"const ccol=\{.*?\};", ccol_js, html, count=1, flags=re.S)
    html = re.sub(r"const deslig=\{.*?\};", "const deslig={};", html, count=1, flags=re.S)

    # 6) alert-body / alert-msg (aba Prospecções) — remove claim obsoleta
    html = re.sub(
        r"document\.getElementById\('alert-body'\)\.innerHTML='.*?';",
        "document.getElementById('alert-body').innerHTML='Sincronizado automaticamente do Notion em " + sync_ts + ". Os totais abaixo refletem a Etapa \\'Prospecção\\' da base Carteira de ECs.';",
        html, count=1, flags=re.S,
    )
    html = html.replace(
        "const MSG='Equipe, a redistribuição das carteiras está no ar. Cada um já pode conferir no dashboard quais ECs assumiu. Confiram o status de cada cliente antes da visita e registrem a devolutiva no mesmo dia. Quem recebeu EC com POS já entregue: prioridade é a visita de pós-venda. Conto com vocês!';",
        "const MSG='Equipe, o dashboard agora sincroniza automaticamente com o Notion 2x ao dia. Confiram o status de cada EC antes da visita e mantenham o Notion atualizado — é a fonte oficial dos dados.';",
    )
    html = html.replace(
        '<div class="alert-title">Redistribuicao de carteiras &middot; 67 ECs remanejados</div>',
        '<div class="alert-title">Funil de prospecção</div>',
    )

    # 7) renderFechamento — mês corrente dinâmico em vez de Julho/2026 fixo
    old_fech = re.search(r"function renderFechamento\(\)\{.*?\n\}\n", html, flags=re.S)
    assert old_fech, "renderFechamento not found"
    new_fech = """function renderFechamento(){
  var hoje=new Date();
  var refDate=new Date(hoje.getFullYear(),hoje.getMonth()-1,1); // mes de fechamento = mes anterior completo
  var prevDate=new Date(hoje.getFullYear(),hoje.getMonth()-2,1);
  var refKey=String(refDate.getMonth()+1).padStart(2,'0')+'/'+refDate.getFullYear();
  var prevKey=String(prevDate.getMonth()+1).padStart(2,'0')+'/'+prevDate.getFullYear();
  var DIAS_UTEIS=0;
  var dCursor=new Date(refDate.getFullYear(),refDate.getMonth(),1);
  while(dCursor.getMonth()===refDate.getMonth()){var wd=dCursor.getDay();if(wd!==0&&wd!==6)DIAS_UTEIS++;dCursor.setDate(dCursor.getDate()+1);}
  var jul=ECS.filter(function(r){return r.d && r.d.slice(3)===refKey;});
  var jun=ECS.filter(function(r){return r.d && r.d.slice(3)===prevKey;});
  var totJul=jul.length, totJun=jun.length;
  var metaJul=jul.reduce(function(a,r){return a+r.m;},0);
  var byc={};
  jul.forEach(function(r){var k=r.kf||r.ko||r.k||'Não atribuído';if(!byc[k])byc[k]={n:0,m:0,ecs:[]};byc[k].n++;byc[k].m+=r.m;byc[k].ecs.push(r);});
  var cons=Object.keys(byc).sort(function(a,b){return byc[b].n-byc[a].n;});
  var byd={};
  jul.forEach(function(r){byd[r.d]=(byd[r.d]||0)+1;});
  var dias=Object.keys(byd).sort(function(a,b){return (+a.slice(0,2))-(+b.slice(0,2));});
  var diasComAtividade=dias.length;
  var mediaUtil=DIAS_UTEIS?(totJul/DIAS_UTEIS):0;
  var pico=dias.length?dias.reduce(function(mx,d){return byd[d]>byd[mx]?d:mx;},dias[0]):null;
  var delta=totJun?Math.round((totJul-totJun)/totJun*100):0;

  var mesNomes=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  var mesLabel=mesNomes[refDate.getMonth()]+'/'+refDate.getFullYear();
  document.querySelector('#tab-fechamento .section-title').textContent='Fechamento de '+mesLabel+' — produção de cadastros';
  document.getElementById('fech-periodo').textContent='01 a '+(new Date(refDate.getFullYear(),refDate.getMonth()+1,0)).getDate()+'/'+String(refDate.getMonth()+1).padStart(2,'0')+'/'+refDate.getFullYear()+' · '+diasComAtividade+' dias com produção';
  var kp=[
    {label:'Cadastros no mês',value:totJul,sub:mesLabel.toLowerCase(),color:'var(--gold)',delta:(delta>=0?'+':'')+delta+'% vs mês anterior',dc:delta>=0?'delta-up':'delta-warn'},
    {label:'Consultores ativos',value:cons.length,sub:'cadastraram no mês',color:'var(--teal)',delta:'',dc:''},
    {label:'Média por dia útil',value:mediaUtil.toFixed(1).replace('.',','),sub:'em '+DIAS_UTEIS+' dias úteis',color:'var(--blue)',delta:'',dc:''},
    {label:'Média/dia ativo',value:diasComAtividade?(totJul/diasComAtividade).toFixed(1).replace('.',','):'0',sub:diasComAtividade+' dias com cadastro',color:'var(--purple)',delta:'',dc:''},
    {label:'Meta TPV gerada',value:brl(metaJul),sub:'no mês',color:'var(--green)',delta:'',dc:''},
    {label:'Melhor dia',value:pico?pico.slice(0,5):'—',sub:pico?byd[pico]+' cadastros':'',color:'var(--gold2)',delta:'',dc:''},
  ];
  document.getElementById('fech-kpis').innerHTML=kp.map(function(k){return '<div class="kpi"><div class="kpi-accent" style="background:'+k.color+'"></div><div class="kpi-label">'+k.label+'</div><div class="kpi-value">'+k.value+'</div><div class="kpi-sub">'+k.sub+'</div>'+(k.delta?'<span class="kpi-delta '+k.dc+'">'+k.delta+'</span>':'')+'</div>';}).join('');

  document.getElementById('fech-count').textContent=totJul+' cadastros no mês';
  document.getElementById('tbody-fech').innerHTML=cons.map(function(k,i){
    var v=byc[k];
    var det=v.ecs.map(function(x){var dono=(x.kn&&x.kn!==k)?' <span style="color:var(--text3)">&rarr; hoje com '+x.kn+'</span>':'';return '<div style="padding:3px 0">&bull; <strong>'+x.e+'</strong> <span style="color:var(--text3)">('+x.d+')</span> &middot; '+x.g+dono+'</div>';}).join('');
    return '<tr style="cursor:pointer" onclick="toggleFech('+i+')"><td class="rank">'+(i+1)+'</td><td class="ec-name">'+k+' <span style="color:var(--text3);font-size:10px">&#9662;</span></td><td style="font-weight:700;color:var(--gold)">'+v.n+'</td><td style="color:var(--text2)">'+(DIAS_UTEIS?(v.n/DIAS_UTEIS).toFixed(2).replace('.',','):'0')+'</td><td style="color:var(--teal);font-weight:600">'+brlFull(v.m)+'</td><td style="color:var(--text3)">'+(totJul?Math.round(v.n/totJul*100):0)+'%</td></tr><tr id="fd'+i+'" style="display:none"><td></td><td colspan="5" style="font-size:12px;color:var(--text2);background:var(--bg2);padding:10px 16px">'+det+'</td></tr>';
  }).join('');

  var col=cons.map(function(_,i){return PAL[i%PAL.length];});
  mk('c-fech-cons',{type:'bar',data:{labels:cons,datasets:[{data:cons.map(function(k){return byc[k].n;}),backgroundColor:col.map(function(c){return c+'66';}),borderColor:col,borderWidth:1.5,borderRadius:4,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{ticks:Object.assign({stepSize:5},TICK),grid:GRID,beginAtZero:true},y:{ticks:{font:{size:11},color:'#8B92A8'},grid:{display:false}}}}});

  mk('c-fech-dia',{type:'bar',data:{labels:dias.map(function(d){return d.slice(0,5);}),datasets:[{data:dias.map(function(d){return byd[d];}),backgroundColor:'#C9A84C55',borderColor:'#C9A84C',borderWidth:1.5,borderRadius:4,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{font:{size:9},color:'#8B92A8',autoSkip:false,maxRotation:60},grid:GRID},y:{ticks:Object.assign({stepSize:2},TICK),grid:GRID,beginAtZero:true}}}});
}
"""
    html = html[:old_fech.start()] + new_fech + html[old_fech.end():]
    html = html.replace(
        'Base: mês de julho pela DATA DE CADASTRO. O crédito fica com quem cadastrou o EC. Exceção: cadastros de consultores desligados são creditados a quem assumiu a carteira (marcados em amarelo no detalhe). Dia útil = 23 dias em julho/2026. <strong style="color:var(--gold2)">Clique no nome do consultor para ver os ECs que ele cadastrou.</strong>',
        'Base: mês anterior completo, pela DATA DE CADASTRO. O crédito fica com quem cadastrou o EC. <strong style="color:var(--gold2)">Clique no nome do consultor para ver os ECs que ele cadastrou.</strong>',
    )
    html = html.replace('Fechamento de Julho/2026 — produção de cadastros', 'Fechamento — produção de cadastros')
    html = html.replace('Cadastros por consultor — Julho', 'Cadastros por consultor — mês')
    html = html.replace('Cadastros por dia — Julho', 'Cadastros por dia — mês')
    html = html.replace('Produção individual — Julho', 'Produção individual — mês')

    # 8) Aba "Situação (Diretoria)" — bloco estático gerado a partir dos dados atuais
    situacao_html = build_situacao_html(ecs, alertas, sync_ts)
    html = re.sub(
        r'(<div class="alert-body">Quadro gerado a partir da planilha &mdash; atualiza sozinho a cada carga\.</div>\n)(.*?)(\n      </div>\n    </div>\n\n<div class="section-header"><div class="section-title">Estágio de cada cliente)',
        lambda m: m.group(1) + situacao_html + m.group(3),
        html, count=1, flags=re.S,
    )

    # 9) Hero subtitle — indicador de última sincronização
    html = re.sub(
        r'(<div class="hero-left">)',
        r'\1<!--SYNC:' + sync_ts + '-->',
        html, count=1,
    )
    m = re.search(r'<div class="hero-left">.*?<p>(.*?)</p>', html, flags=re.S)
    if m:
        old_p = m.group(0)
        new_p = old_p.rsplit('<p>', 1)[0] + '<p>' + m.group(1) + ' <span style="color:var(--text3)">· sincronizado com o Notion em ' + sync_ts + '</span></p>'
        html = html.replace(old_p, new_p, 1)

    # 10) Botao de periodo para o mes atual, se ainda nao existir
    hoje = date.today()
    mes_atual_key = f'{hoje.month:02d}/{hoje.year}'
    mes_nomes = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    mes_label = mes_nomes[hoje.month-1]
    if f"setPeriod('{mes_atual_key}'" not in html:
        html = html.replace(
            "<button class=\"period-btn\" onclick=\"setPeriod('07/2026',this)\">Julho</button>",
            "<button class=\"period-btn\" onclick=\"setPeriod('07/2026',this)\">Julho</button>\n      <button class=\"period-btn\" onclick=\"setPeriod('" + mes_atual_key + "',this)\">" + mes_label + "</button>",
        )

    sys.stdout.write(html)

if __name__ == '__main__':
    main()
