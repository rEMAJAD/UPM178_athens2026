"""Build a six-page report entirely from saved, verified experiment records."""
from pathlib import Path
import json
from collections import Counter
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
STUDENT='[Name] [Surname]'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodySmall',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=7))
styles.add(ParagraphStyle(name='NoteSmall',fontName='Helvetica',fontSize=7.5,leading=10,spaceAfter=5,textColor=colors.HexColor('#465568')))
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=22,leading=27,spaceAfter=15,textColor=colors.HexColor('#13364d')))
styles['Heading1'].textColor=colors.HexColor('#13364d')
styles['Heading1'].fontSize=16
styles['Heading2'].fontSize=11
story=[]


def p(text,style='BodySmall'):
    story.append(Paragraph(text,styles[style]))


def title(text): p(text,'Heading1')
def h(text): p(text,'Heading2')
def page(): story.append(PageBreak())
def figure(path,width=480):
    from PIL import Image as PILImage
    with PILImage.open(path) as im: w,hh=im.size
    story.append(Image(str(path),width=width,height=width*hh/w))
    story.append(Spacer(1,6))


def table(rows,widths=None,size=8):
    t=Table([[str(v) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#163e56')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),size),
        ('LEADING',(0,0),(-1,-1),size+2),('TOPPADDING',(0,0),(-1,-1),3 if size<8 else 4),('BOTTOMPADDING',(0,0),(-1,-1),3 if size<8 else 4),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eff4f7'),colors.white]),
        ('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(t); story.append(Spacer(1,8))


def fmt(value,digits=3):
    if value is None: return 'N/A'
    return f'{value:.{digits}f}' if isinstance(value,float) else str(value)


def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))


def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#b6c7d3')); canvas.line(42,36,A4[0]-42,36)
    canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#465568'))
    canvas.drawString(42,24,'UPM178 | Radio Coverage Optimization | November 2026')
    canvas.drawRightString(A4[0]-42,24,str(doc.page))


def main():
    rows=load('results/benchmark/benchmark.json')
    acc=load('results/accuracy/accuracy.json')
    sweep=load('results/coverage_sweep/coverage_sweep.json')
    env=load('results/benchmark/environment.json')
    if len(rows)!=60 or any(r['objective'] is not None and not r['verified'] for r in rows):
        raise ValueError('Report expects 60 measured runs with verified incumbents where available')
    title_text='Radio Coverage, Antenna Height and Power Optimization Using Constraint Programming'
    p(title_text,'ReportTitle')
    p(f'<b>Student:</b> {STUDENT}<br/><b>Course:</b> UPM178, Universidad Politecnica de Madrid<br/><b>Submission:</b> November 2026')
    h('1. Problem and motivation')
    p('Radio planning involves a trade-off between deployment cost and geographical service. '
      'This project jointly chooses which candidate base stations to activate and their antenna heights and transmitter powers '
      'on a synthetic 10 x 10 km urban area. Higher antennas generally reach farther but incur higher '
      'construction costs. A CP optimizer, rather than a greedy placement rule, selects the deployment.')
    h('2. Discrete constraint optimization model')
    p('Let i index N candidate sites, k index K heights, p index P powers, and j index M '
      'receiver samples. The fixed binary tensor A[i,k,p,j] states whether a configuration reaches '
      'a sample. c[i,k,p] is its integer deployment cost. Decision x[i,k,p] belongs to {0,1}; Boolean y[j] '
      'indicates actual sample coverage. The model is:')
    table([['Component','Definition'],['Site choice','sum_(k,p) x[i,k,p] <= 1 for each site i'],
           ['Local height limit','x[i,k,p] = 0 whenever heights[k] > max_height[i]'],
           ['Site separation','not (active[i] and active[t]) if distance(i,t) < 2 km'],
           ['Station count','links[j] = sum_(i,k,p: A[i,k,p,j]=1) x[i,k,p]'],
           ['Coverage link','y[j] iff links[j] >= 1'],
           ['Critical points','links[j] >= 2 for every critical point j'],
           ['Required coverage','sum_j y[j] >= ceil(target_percent M / 100)'],
           ['Objective','minimize sum_(i,k,p) c[i,k,p] x[i,k,p]']],widths=[115,390])
    p('The implementation uses equivalence, so a sample cannot be credited without a supporting station. '
      'At 100% coverage every sample must be served. Heights are 30, 50, 80 and 120 m. '
      'One height/power configuration is allowed per site, so two supporting configurations must be at distinct sites. Site-specific height '
      'limits represent local construction restrictions; an antenna equal to the limit is permitted.')
    h('3. Propagation and discretization')
    p('The small/medium-city urban Okumura-Hata formula is evaluated in Python with real-valued '
      'arithmetic. With frequency f in MHz, antenna heights hb and hm in metres, and distance d in km:')
    p('a(hm) = (1.1 log10(f) - 0.7) hm - (1.56 log10(f) - 0.8)<br/>'
      'L = 69.55 + 26.16 log10(f) - 13.82 log10(hb) - a(hm)<br/>'
      '&nbsp;&nbsp;&nbsp;&nbsp;+ (44.9 - 6.55 log10(hb)) log10(d)<br/>'
      'Prx = Ptx + Gtx + Grx - Lfeeder - L')
    p('Defaults are f=900 MHz, hm=1.5 m, Ptx=34/37/40/43 dBm, Gtx=15 dBi, Grx=0 dBi and feeder loss=2 dB. '
      'Sensitivity -95 dBm plus a 10 dB margin gives a -85 dBm threshold, or 132/135/138/141 dB maximum path loss, respectively. '
      'A[i,k,p,j] is 1 precisely when Prx meets this threshold. Nonlinear logarithms never enter MiniZinc.')
    p('The empirical ranges are f=150-1500 MHz, hb=30-200 m, hm=1-10 m and d=1-20 km. '
      'Distances below 1 km are clamped to 1 km. This is a conservative simplification relative to '
      'extrapolation, not an accurate near-field prediction or guaranteed physical bound. Values outside '
      'the other ranges are rejected. The model omits interference, terrain, traffic and fading.','NoteSmall')

    page(); title('4. Dataset construction and complexity')
    p('Ten instances use fixed seeds 17801-17810. Candidate coordinates are an explicit fixed list in settings.py; each dataset uses its first N entries. The first nine sites '
      'provide a feasible witness using the highest permitted antenna and power at each site; selected sites must be at least 2 km apart. Seeds affect only costs. Costs equal '
      'a random site base (65-150 units) plus increasing height premiums (25, 65, 130, 235 units) '
      'scaled by a site-specific multiplier in [0.8,1.25]. Power choices 34/37/40/43 dBm add 0/15/35/60 cost units, respectively. Costs are synthetic, not market prices. '
      'Local height limits repeat the sequence [50,80,120,50,80,120,80,50,120,50] metres. '
      'No deployment solution is hardcoded or passed as a warm start.')
    summary=[['Data','N','M','Binary entries','Best cost','Proof found?']]
    for idx in range(1,11):
        rs=[r for r in rows if r['instance']==f'instance_{idx:02d}']; best=min((r['objective'] for r in rs if r['objective'] is not None),default='N/A')
        r=rs[0]; summary.append([f'{idx:02d}',r['n'],r['m'],r['n']*4*4*r['m'],best,'Yes' if any(x['proven_optimal'] for x in rs) else 'No'])
    table(summary,[43,40,49,115,95,110])
    p('Every generated instance is checked for feasibility and rejected if one station alone meets '
      'the target. Optimization grids include the boundary plus two fixed critical points: hospital (3,3) and campus (7,7) km. Each critical point requires two BTS, even below a 100% overall target. Coordinates, costs, physical parameters '
      'and a DZN checksum are stored in adjacent JSON metadata. Coverage storage scales as O(NKPM); the precomputed distance-conflict table takes O(N^2). '
      'There are (KP+1)^N possible site/height/power deployments before propagation.')
    h('Modeling choices and propagation')
    p('A binary encoding makes costs linear and coverage a reified sum. At full coverage, all y variables '
      'must be true; a sample with one remaining supporter can force that configuration. Site exclusivity '
      'then eliminates its other height/power choices. The objective bound prunes expensive partial deployments. '
      'This is qualitative analysis: no claim is made that a particular domain/bounds consistency level '
      'was explicitly enforced. Gecode chooses its normal flattened-model propagators.')
    p('No alternative encoding, symmetry breaking, redundant constraints or dominance filtering was '
      'added. Candidate coordinates and costs distinguish sites, so arbitrary ordering constraints '
      'could remove valid optima. A taller configuration is not automatically dominant because it '
      'costs more. The controlled experiment varies search annotations on the same model.')
    figure(ROOT/'results/deployment/comparison.png',width=480)
    p('The radio reference activates all candidates at their highest permitted height and power, ignoring spacing. It is not a feasible deployment. The CP deployment mixes antenna '
      'heights and reduces cost. Both displayed coverage percentages use the independent dense grid.','NoteSmall')

    labels={'input_min':'IM','first_min':'FM','first_max':'FX','degree_max':'DX','weighted_random':'WR','weighted_luby':'WL'}
    for start,end in [(1,5),(6,10)]:
        page(); title(f'5. Search experiments: datasets {start:02d}-{end:02d}')
        if start==1:
            p(f'All runs use MiniZinc 2.10.1, Gecode 6.4.0, one solver thread, seed 178 and a '
              f'{rows[0]["limit_seconds"]:g} s total MiniZinc budget including compilation. Runs in the final '
              'benchmark are sequential. This is a short pilot, not a 15-minute evaluation. The CLI default '
              'is 900 s. Hardware: '+escape(env['processor'])+'. Python '+env['python']+'.')
        else:
            p('The same settings apply. P indicates a proven optimum; T is a verified feasible incumbent '
              'at the time limit. Costs from T runs are upper bounds, not proven minima. All verified incumbents cover every sample. U means no solution found before timeout.')
        p('IM=input_order/min; FM=first_fail/min; FX=first_fail/max; DX=most_constrained/max; '
          'WR=dom_w_deg/random; WL=dom_w_deg/random + Luby(100). IM/FM/FX/DX/WR have no restarts. '
          'The min/max/random names refer to indomain value annotations. P=proven optimum; T=time-limited incumbent; U=no solution found.','NoteSmall')
        t=[['Data','Search','Cost','S','Solve s','Failures','Nodes','Propagations','Props','Restarts']]
        for r in rows:
            idx=int(r['instance'].split('_')[-1])
            if start<=idx<=end:
                s=r['statistics']; t.append([f'{idx:02d}',labels[r['strategy']],fmt(r['objective']),
                    'P' if r['proven_optimal'] else ('T' if r['verified'] else 'U'),fmt(s.get('solveTime')),
                    s.get('failures','N/A'),s.get('nodes','N/A'),s.get('propagations','N/A'),s.get('propagators','N/A'),s.get('restarts','N/A')])
        table(t,[28,32,36,22,42,57,57,80,40,47],size=7)
        p('Props = propagators. Nogoods: N/A for every run (not emitted by this Gecode configuration). '
          'Complete CSV/JSON includes wall time, compile/init/solve time, nodes, failures, propagations, '
          'propagators, restarts, timeout and proof status. Raw solver JSONL is retained. No statistics are inferred.','NoteSmall')
        if start==1:
            p('All six search combinations were executed successfully, with no ignored-annotation warnings. '
              'The no-restart setting uses empty_annotation because Gecode warns that restart_none is ignored. '
              'WL is compared with WR to isolate the restart change while keeping variable and value ordering fixed.','NoteSmall')
        else:
            counts=Counter(r['strategy'] for r in rows if r['proven_optimal'])
            p('Proven optima out of ten: '+', '.join(f'{labels[s]} {counts[s]}/10' for s in labels)+'. '
              'Binary domain ties can make first_fail behave like input_order. Trying 1 first may commit to weak low-power configurations and delay feasibility. Failure-weighted ordering '
              'and randomized values can change the search substantially. Restarts are not uniformly beneficial. '
              'A single fixed-seed run per configuration cannot establish statistically robust rankings.','NoteSmall')

    page(); title('6. Discretization accuracy and coverage trade-offs')
    p('The accuracy experiment fixes 20 candidate sites, costs, powers, height/spacing limits, two critical coordinates and seed 17803 while changing '
      'only the receiver grid. Each solution is evaluated on an independent 100 x 100 grid of cell centres '
      '(10,000 points). Optimization samples include the boundary and two fixed critical points, so M is grid size plus two. The same '
      f'{acc[0]["strategy"]} search and {acc[0]["limit_seconds"]:g} s budget are used for every resolution.')
    table([['Grid','Cost','Proof','Sample %','Validation %','Wall s']]+
          [[f'{int(r["m"]**.5)} x {int(r["m"]**.5)}',fmt(r['objective']),'Yes' if r['proven_optimal'] else 'No',
            fmt(r.get('coverage_percent'),2),fmt(r.get('validation_percent'),2),fmt(r['total_runtime'])] for r in acc],
          [80,70,65,90,100,80])
    figure(ROOT/'results/accuracy/accuracy.png',width=500)
    p('Sample coverage is not a mathematical guarantee of continuous geographical coverage. '
      'Finer grids detect gaps between coarse samples but require larger tensors and more compilation '
      'and search work. These boundary-inclusive grids are not nested, so even proven costs need not '
      'increase monotonically with resolution. If a run is not proven optimal, search quality is an '
      'additional confounder; cost differences must not be attributed to discretization alone.')
    h('Cost of stricter coverage on dataset 01')
    table([['Required %','Cost','Achieved sample %','Proven optimum']]+
          [[r['minimum_percent'],fmt(r['objective']),fmt(r.get('coverage_percent'),2),'Yes' if r['proven_optimal'] else 'No'] for r in sweep],
          [100,100,150,135])
    p('The coverage sweep keeps sites, costs and receiver points fixed and changes only the minimum '
      'coverage proportion. Fractional required counts are rounded upward. The wider model can therefore '
      'trade cost against missed samples without counting the same sample twice.')
    p('Wall time covers the MiniZinc process, including compilation and solving; Python generation, verification '
      'and plotting are excluded. Runtime figures are machine-dependent. Seeds and raw inputs reproduce the instance and search '
      'settings; wall-clock limits can change the final incumbent across machines and runs. Compare '
      'proof status and objective alongside timing, rather than treating equal budgets as equal search effort.','NoteSmall')

    page(); title('7. Verification, limitations and conclusions')
    p('The automated suite checks independently derived Hata values, threshold equality and margin, '
      'height/distance monotonicity, empirical-range validation, DZN tensor order, reproducible generation, '
      'all ten size profiles, feasibility, exclusive configurations, height/spacing limits, coverage and cost consistency. A four-site, '
      'two-height/two-power example has 5^4=625 assignments; exhaustive enumeration matches the CP optimum for '
      'five coverage targets. Every annotation is also tested through a real Gecode solve, and an '
      'infeasible instance is distinguished from a timeout. Tests check 3 dB power increments, distinct-site backup and critical-point coverage after removing any selected station. Test execution is recorded in results/tests.txt.')
    p('Each accepted solver deployment is checked again against a freshly calculated propagation tensor '
      'in Python. The reported objective must equal the selected site/height/power costs exactly. Invalid '
      'deployments are rejected before plotting. This independent check also applies to benchmark runs.')
    figure(ROOT/'results/deployment/heatmap.png',width=250)
    p('Example: dataset 01 received-power map, recomputed from selected stations. Hatching identifies '
      'dense-grid points below -85 dBm. The best serving signal is plotted; arbitrary coverage circles '
      'and sums of unrelated station powers are not used.','NoteSmall')
    h('Conclusions and outstanding work')
    p('The working CP model jointly optimizes placement, height and power, supports 2,502 optimization samples '
      'and 10,000 validation samples, and requires two-station coverage at critical points. Real measurements demonstrate '
      'the effects of search choices and finite sampling. The larger instances are not all proven optimal '
      'within the pilot budget. Full 900-second runs and repeated random seeds remain future experiments. '
      'Only Windows execution was tested; Linux portability is designed but unverified. Search-tree traces '
      'were not recorded, so no tree diagrams are reconstructed from aggregate statistics.')
    p('Physical conclusions are limited to a homogeneous synthetic urban model and synthetic costs. '
      'Backup protects only the critical points against one BTS outage; capacity after failure is not modeled. Dense-grid validation remains sampled validation. Practical planning would need calibrated terrain, '
      'clutter, interference and demand models. Reproducibility scripts, all ten DZN instances, metadata, '
      'raw logs and machine-readable tables are included. Replace the student placeholders before submission.')
    p('<b>References.</b> UPM178 supplied report rubric; Chapter 2, part 3 (modeling); Chapter 3, parts 1-2 '
      '(propagation, ordering, randomization/restarts); Chapter 4 (optimization). Propagation equation and '
      'parameter ranges follow the supplied project specification. MiniZinc Handbook, Search and Annotations: '
      '<link href="https://docs.minizinc.dev/en/stable/mzn_search.html">docs.minizinc.dev/en/stable/mzn_search.html</link>. '
      'Original submission instructions: named ZIP, at least ten data files, generator and 2-6 page report; '
      'submit before November 20, 2026. No upload is performed.','NoteSmall')
    OUT.mkdir(exist_ok=True)
    doc=SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=36,bottomMargin=45,
                          title=title_text,author=STUDENT)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print(OUT/'report.pdf')


if __name__=='__main__': main()
