// Warna Chart
const colours=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9'];

// Mengurangi jumlah titik data (yang terlalu panjang) untuk meningkatkan kinerja rendering
export function decimate(line) {
    const {x,y}=line, points=[];
    const size=y.length>4000 ? Math.ceil(y.length/2000) : 1;

    let i=0;
    while (i<y.length) {
        if (y[i]===null) { 
            if (points.at(-1)!==null) points.push(null); i++; 
            continue; 
        }
        const start=i;
    
        while (i<y.length && y[i]!==null) i++;
        const end=i;
    
        points.push([x[start],y[start]]);
        for (let a=start;a<end;a+=size) {
            let min=a,max=a;
            for (let j=a+1;j<Math.min(end,a+size);j++) {
            if (y[j]<y[min]) min=j;
            if (y[j]>y[max]) max=j;
            }
            for (const j of min===max?[min]:[min,max].sort((a,b)=>a-b)) points.push([x[j],y[j]]);
        }
        if (end-start>1) points.push([x[end-1],y[end-1]]);
    }
    return points;
}

function ticks(min,max,integers=false) {
    const rough=(max-min)/5, power=10**Math.floor(Math.log10(rough));
    const unit=rough/power, step=Math.max(integers?1:0,(unit<=1?1:unit<=2?2:unit<=5?5:10)*power);
    const values=[];
    for (let v=Math.ceil(min/step)*step;v<=max+step*1e-8 && values.length<20;v+=step) values.push(Math.abs(v)<step*1e-8?0:v);
    return values;
}

const number = value => Math.abs(value)>=1e6 || (value!==0 && Math.abs(value)<.001) ? value.toExponential(1) : value.toLocaleString(undefined,{maximumFractionDigits:3});

// [MAIN] Fungsi untuk membuat grafik  
export function drawLineChart(canvas, chart) {
    
    const ratio=devicePixelRatio||1, width=Math.max(1,canvas.clientWidth), height=Math.max(1,canvas.clientHeight);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);
    ctx.fillStyle='#FFFFFF';ctx.fillRect(0,0,width,height);
    if (!chart) { ctx.fillStyle='#5A6675';ctx.font='13px system-ui';ctx.fillText('Load a result to see its charts.',16,30);return; }
    canvas.setAttribute('aria-label',`${chart.title}. ${chart.x_label}; ${chart.y_label}.`);


    let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity,integerX=true;
    for (const line of chart.lines) for (let i=0;i<line.x.length;i++) {
        const x=line.x[i],y=line.y[i];integerX &&=Number.isInteger(x);
        xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);
        if (y!==null) {ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);}
    }
    
    const hasData=Number.isFinite(ymin);
    if (!Number.isFinite(xmin)) {xmin=0;xmax=1;}
    if (xmin===xmax) {xmin-=.5;xmax+=.5;}
    if (!hasData) {ymin=0;ymax=1;}
    const pad=ymin===ymax?1:(ymax-ymin)*.05;ymin-=pad;ymax+=pad;
    ctx.fillStyle='#1A2230';ctx.font='600 14px system-ui';ctx.fillText(chart.title,0,18,width);
    ctx.font='11px system-ui';
    let legendX=0,legendY=39;
    const many=chart.lines.length>6;
    if (many) {ctx.fillStyle='#5A6675';ctx.fillText(`${chart.lines.length} restarts`,0,legendY);}
    else chart.lines.forEach((line,i)=>{
        const needed=Math.min(width,ctx.measureText(line.name).width+34);
        if (legendX+needed>width && legendX>0) {legendX=0;legendY+=16;}
        ctx.fillStyle=colours[i%colours.length];ctx.fillRect(legendX,legendY-7,14,3);
        ctx.fillStyle='#5A6675';ctx.fillText(line.name,legendX+20,legendY,width-legendX-20);legendX+=needed;
    });
    const left=65,right=width-16,top=legendY+18,bottom=height-43;
    if (right<=left || bottom<=top) return;
    const px=x=>left+(x-xmin)/(xmax-xmin)*(right-left),py=y=>bottom-(y-ymin)/(ymax-ymin)*(bottom-top);
    ctx.lineWidth=1;ctx.strokeStyle='#E5E9EE';ctx.fillStyle='#5A6675';ctx.font='11px system-ui';
    for (const value of ticks(ymin,ymax)) {
        const y=py(value);ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
        ctx.textAlign='right';ctx.fillText(number(value),left-8,y+4,45);
    }
    for (const value of ticks(xmin,xmax,integerX)) {
        const x=px(value);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();
        ctx.textAlign='center';ctx.fillText(number(value),x,bottom+17);
    }
    ctx.strokeStyle='#7D8FA3';ctx.beginPath();ctx.moveTo(left,top);ctx.lineTo(left,bottom);ctx.lineTo(right,bottom);ctx.stroke();
    ctx.textAlign='center';ctx.fillStyle='#5A6675';ctx.fillText(chart.x_label,(left+right)/2,height-5,right-left);
    ctx.save();ctx.translate(12,(top+bottom)/2);ctx.rotate(-Math.PI/2);ctx.fillText(chart.y_label,0,0,bottom-top);ctx.restore();
    if (!hasData) {ctx.fillText('No finite values',(left+right)/2,(top+bottom)/2);return;}
    ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();
    chart.lines.forEach((line,i)=>{
        ctx.strokeStyle=many?'#7D8FA3':colours[i%colours.length];ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=many?1:1.8;
        let segment=[],points=decimate(line);
        function flush() {
        if (!segment.length) return;
        ctx.beginPath();ctx.moveTo(px(segment[0][0]),py(segment[0][1]));
        for (const [x,y] of segment.slice(1)) ctx.lineTo(px(x),py(y));ctx.stroke();
        if (segment.every(p=>p[0]===segment[0][0])) {ctx.beginPath();ctx.arc(px(segment[0][0]),py(segment[0][1]),3,0,Math.PI*2);ctx.fill();}
        segment=[];
        }
        for (const point of points) {if (point===null) flush();else segment.push(point);}flush();
    });
    ctx.restore();
}
