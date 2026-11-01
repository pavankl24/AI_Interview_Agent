// Local UI preview server. Interview endpoints here are scripted demo data;
// use `uvicorn api:app --reload` to connect the app to the live Groq-backed API.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const port = Number(process.env.PORT || 4173);
const questions = [
  'Could you tell me what interests you about working with ' ,
  'How would you explain a concept from this topic to a teammate who is new to it?',
  'Can you walk me through how you would solve a small, practical problem in this area?',
  'Tell me about a challenge you faced while learning or building something. What did you do?',
  'What would you like to get better at next in this topic?'
];
let current = null;

function send(res, status, body, type='application/json; charset=utf-8') {
  res.writeHead(status, {'Content-Type':type, 'Cache-Control':'no-store'});
  res.end(type.startsWith('application/json') ? JSON.stringify(body) : body);
}
function readBody(req) {
  return new Promise((resolve,reject)=>{let raw='';req.on('data',chunk=>raw+=chunk);req.on('end',()=>{try{resolve(JSON.parse(raw||'{}'))}catch(e){reject(e)}});req.on('error',reject)});
}
const server = http.createServer(async (req,res)=>{
  const url = new URL(req.url,'http://127.0.0.1');
  try {
    if (req.method==='POST' && url.pathname==='/interview/start') {
      const body=await readBody(req);
      current={topic:String(body.interview_type||'Python'),limit:Math.max(1,Math.min(50,Number(body.max_questions)||5)),number:1,answers:[]};
      return send(res,200,{question_number:1,max_questions:current.limit,question:`${questions[0]}${current.topic}?`,interview_completed:false});
    }
    if (req.method==='POST' && url.pathname==='/interview/answer') {
      const body=await readBody(req);
      if(!current)return send(res,404,{detail:'No active interview.'});
      current.answers.push(String(body.answer||''));
      if(current.number>=current.limit){
        const score=Math.min(9.6,Math.max(5.8,6.2+current.answers.reduce((n,a)=>n+Math.min(a.trim().length,160)/220,0))).toFixed(1);
        const report={interview_type:current.topic,knowledge_score:Number(score),problem_solving_score:null,overall_score:Number(score),strengths:['You shared your reasoning clearly.','You stayed engaged throughout the practice.'],weaknesses:['A couple of answers could use more detail.'],areas_to_improve:['Add a specific example to support your key points.','Pause briefly to structure longer answers.'],overall_feedback:'A thoughtful practice. Your answers showed curiosity and a solid foundation. With a little more detail and a concrete example or two, you’ll make an even stronger impression.'};
        current=null;
        return send(res,200,{evaluation:'Interview completed.',interview_completed:true,report});
      }
      current.number++;
      const q=questions[(current.number-1)%questions.length];
      return send(res,200,{evaluation:'Thanks for sharing that. Let’s explore one more angle.',question_number:current.number,max_questions:current.limit,question:q.includes('this topic')?q.replace('this topic',current.topic):q,interview_completed:false});
    }
    if(req.method==='POST'&&url.pathname==='/interview/finish'){
      if(!current)return send(res,404,{detail:'No active interview.'});
      const topic=current.topic;current=null;
      return send(res,200,{interview_type:topic,knowledge_score:7,problem_solving_score:null,overall_score:7,strengths:['You made a good start.'],weaknesses:['Try adding more detail.'],areas_to_improve:['Use a concrete example.'],overall_feedback:'Thanks for practicing today.'});
    }
    if(req.method!=='GET'&&req.method!=='HEAD')return send(res,405,{detail:'Method not allowed.'});
    const pathname=decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname);
    const file=path.resolve(root,'.'+pathname);
    if(!file.startsWith(root+path.sep)&&file!==root)return send(res,403,{detail:'Forbidden.'});
    if(!fs.existsSync(file)||!fs.statSync(file).isFile())return send(res,404,{detail:'Not found.'});
    const ext=path.extname(file).toLowerCase();
    const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon'};
    res.writeHead(200,{'Content-Type':types[ext]||'application/octet-stream','Cache-Control':'no-store'});
    if(req.method==='HEAD')return res.end();
    fs.createReadStream(file).pipe(res);
  } catch (error) {
    send(res,500,{detail:'Preview server error.'});
  }
});
server.listen(port,'127.0.0.1',()=>console.log(`Prepwise UI demo: http://127.0.0.1:${port}`));
