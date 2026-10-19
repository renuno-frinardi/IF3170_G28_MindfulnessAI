// File untuk menampilkan 3D viewer untuk paket (WebGL)

// Fungsi-fungsi vektor dan matriks
// 1. Pengurangan
const subtract = (a, b) => a.map((v, i) => v - b[i]);
// 2. Dot product
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
// 3. Cross Product
const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
// 4. Normalisasi
const normalize = v => { const length = Math.hypot(...v); return v.map(x => x / length); };
// 5. Perkalian matriks 4x4
function multiply(a, b) {
  const out = new Float32Array(16);
  for (let c=0; c<4; c++) for (let r=0; r<4; r++)
    for (let k=0; k<4; k++) out[c*4+r] += a[k*4+r]*b[c*4+k];
  return out;
}

// Fungsi-fungsi untuk membuat matriks transformasi 3D
// 1. Membuat matriks proyeksi perspektif 4x4  
function perspective(fov, aspect, near, far) {
  const f = 1 / Math.tan(fov / 2), d = near - far;
  return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)/d,-1, 0,0,2*far*near/d,0]);
}

// 2. Membuat matriks kamera dari posisi mata (eye) ke titik tengah objek (target)
function lookAt(eye, target) {
  const z = normalize(subtract(eye, target)), x = normalize(cross([0,0,1], z)), y = cross(z, x);
  return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0, -dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
}


// Variabel warna untuk visualisasi
const hex = value => [1,3,5].map(i => parseInt(value.slice(i, i+2), 16) / 255);
const mix = (a, b, t) => a.map((v, i) => v*(1-t) + b[i]*t);
const low = hex('#CFE0EC'), high = hex('#17456E'), ink = hex('#1A2230');


// [Main] Fungsi utama untuk membuat viewer 3D
export function createViewer(canvas) {
    
    // Variabel WebGL dibuat 
    const gl = canvas.getContext('webgl', {antialias:true, preserveDrawingBuffer:true});
    if (!gl) return null;

    function shader(type, source) {
        const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s);

        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
        return s;
    }
    const program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, `
        attribute vec3 aPos, aNormal;
        uniform mat4 uVP;
        uniform vec3 uOffset, uSize;
        varying vec3 vNormal;
        void main() { vNormal=aNormal; gl_Position=uVP*vec4(aPos*uSize+uOffset,1.0); }
        `)
    );

    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, `
        precision mediump float;
        uniform vec3 uColor;
        uniform bool uLit;
        varying vec3 vNormal;
        void main() {
            float light=uLit ? 0.55+0.45*max(dot(normalize(vNormal),normalize(vec3(0.35,-0.5,0.8))),0.0) : 1.0;
            gl_FragColor=vec4(uColor*light,1.0);
        }
        `)
    );
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));

    // Konstanta
    const uniforms = Object.fromEntries(['uVP','uOffset','uSize','uColor','uLit'].map(n => [n,gl.getUniformLocation(program,n)]));
    const position = gl.getAttribLocation(program,'aPos'), normal = gl.getAttribLocation(program,'aNormal');
    const corners = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]];
    const faces = [[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]];
    const normals = [[0,0,-1],[0,0,1],[0,-1,0],[0,1,0],[-1,0,0],[1,0,0]];
    const vertices = [];
    faces.forEach((face, i) => [0,1,2,0,2,3].forEach(j => vertices.push(...corners[face[j]], ...normals[i])));
    const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]].flatMap(edge => edge.flatMap(i => corners[i]));
    function buffer(values) {
    const b=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,b); gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW); return b;
    }
    const faceBuffer=buffer(vertices), edgeBuffer=buffer(edges);
    let state=null, boxes=[], mode='value', highlight=null, target=[0,0,0], diagonal=1;
    let yaw=-1, pitch=.45, distance=1.6, pending=false, lastPointer=null;

    // Fungsi untuk menandai bahwa gambar perlu di-update (apabila kamera digeser)
    function dirty() {
        if (!pending) { pending=true; requestAnimationFrame(() => { pending=false; draw(); }); }
    }
    function resetCamera() { 
        yaw=-1; pitch=.45; distance=diagonal*1.6; dirty(); 
    }
    function setState(next, opts={}) {
        const changed = next !== state;
        state=next; mode=opts.colorMode ?? mode; highlight=opts.highlightId ?? null;
        if (!changed) { dirty(); return; }
        boxes=[];
        if (!state) { dirty(); return; }
        const {w,l,h}=state.truck;
        let x=w+Math.max(1,.15*w), y=0, columnWidth=0;
        for (const p of state.packages) {
            let min=p.pos;
            if (min===null) {
            if (y>0 && y+p.dims[1]>Math.max(l,1)) { x+=columnWidth+.5; y=0; columnWidth=0; }
            min=[x,y,0]; y+=p.dims[1]+.5; columnWidth=Math.max(columnWidth,p.dims[0]);
            }
            boxes.push({id:p.id,min,size:p.dims,value:p.value,fragile:p.fragile,loaded:p.pos!==null});
        }
        const minimum=[0,0,0], maximum=[w,l,h];
        for (const b of boxes) for (let i=0;i<3;i++) {
            minimum[i]=Math.min(minimum[i],b.min[i]); maximum[i]=Math.max(maximum[i],b.min[i]+b.size[i]);
        }
        target=minimum.map((v,i)=>(v+maximum[i])/2); diagonal=Math.max(1,Math.hypot(...subtract(maximum,minimum)));
        resetCamera();
    }

    // Merubah persepsi kamera dan menggambar ulang gambar 3D
    function draw() {
        const ratio=devicePixelRatio || 1, width=Math.max(1,Math.round(canvas.clientWidth*ratio)), height=Math.max(1,Math.round(canvas.clientHeight*ratio));
        if (canvas.width!==width || canvas.height!==height) { canvas.width=width; canvas.height=height; }
        gl.viewport(0,0,width,height); gl.clearColor(.956,.965,.973,1); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
        if (!state) return;
        gl.useProgram(program); gl.enable(gl.DEPTH_TEST);
        const eye=target.map((v,i)=>v+distance*[Math.cos(pitch)*Math.cos(yaw),Math.cos(pitch)*Math.sin(yaw),Math.sin(pitch)][i]);
        gl.uniformMatrix4fv(uniforms.uVP,false,multiply(perspective(40*Math.PI/180,width/height,.01*diagonal,20*diagonal),lookAt(eye,target)));
        const values=boxes.map(b=>b.value), min=Math.min(...values), max=Math.max(...values);
        const {w,l,h}=state.truck;
        function box(b, colour, lines=false) {
            const selected=b.id!==undefined && b.id===highlight;
            gl.uniform3fv(uniforms.uOffset,selected ? b.min.map(v=>v-.02) : b.min);
            gl.uniform3fv(uniforms.uSize,selected ? b.size.map(v=>v+.04) : b.size);
            gl.uniform3fv(uniforms.uColor,selected ? hex('#D23F4A') : colour);
            gl.drawArrays(lines?gl.LINES:gl.TRIANGLES,0,lines?24:36);
        }
        gl.bindBuffer(gl.ARRAY_BUFFER,faceBuffer); gl.enableVertexAttribArray(position); gl.enableVertexAttribArray(normal);
        gl.vertexAttribPointer(position,3,gl.FLOAT,false,24,0); gl.vertexAttribPointer(normal,3,gl.FLOAT,false,24,12);
        gl.uniform1i(uniforms.uLit,1); gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1,1);
        box({min:[0,0,-.02],size:[w,l,.02]},hex('#E1E6EC'));
        for (const b of boxes) {
            let colour=mode==='fragility' ? hex(b.fragile?'#E39B1B':'#7D8FA3') : mix(low,high,max===min?.5:(b.value-min)/(max-min));
            if (!b.loaded) colour=mix(colour,hex('#C9CED5'),.65);
            box(b,colour);
        }
        gl.disable(gl.POLYGON_OFFSET_FILL); gl.uniform1i(uniforms.uLit,0);
        gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer); gl.vertexAttribPointer(position,3,gl.FLOAT,false,0,0);
        gl.disableVertexAttribArray(normal); gl.vertexAttrib3f(normal,0,0,1);
        for (const b of boxes) box(b,b.loaded?ink:mix(ink,hex('#C9CED5'),.5),true);
        box({min:[0,0,0],size:[w,l,h]},ink,true);
    }


    // Event listener untuk interaksi pengguna
    canvas.addEventListener('pointerdown',e=>{ lastPointer=[e.clientX,e.clientY]; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener('pointermove',e=>{
        if (!lastPointer) return;
        yaw-=(e.clientX-lastPointer[0])*.008; pitch=Math.max(-Math.PI/2+.05,Math.min(Math.PI/2-.05,pitch+(e.clientY-lastPointer[1])*.008));
        lastPointer=[e.clientX,e.clientY]; dirty();
        }
    );
    canvas.addEventListener('lostpointercapture',()=>{lastPointer=null;});
    canvas.addEventListener('pointerup',()=>{lastPointer=null;});
    canvas.addEventListener('wheel',e=>{ e.preventDefault(); distance=Math.max(diagonal*.35,Math.min(diagonal*8,distance*Math.exp(e.deltaY*.001))); dirty(); },{passive:false});
    canvas.addEventListener('dblclick',resetCamera);
    new ResizeObserver(dirty).observe(canvas.parentElement); dirty();
    return {
        setState, resetCamera,
        setColorMode(value) { mode=value; dirty(); },
        setHighlight(id) { highlight=id; dirty(); },
        toPNG() { 
            draw(); 
            return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('PNG Export Gagal!')))); 
        },
    };
}
