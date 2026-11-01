// Local UI preview server. Interview endpoints here are scripted demo data;
// use `uvicorn api:app --reload` to connect the app to the live Groq-backed API.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const port = Number(process.env.PORT || 4174);
let current = null;

function questionFor(interview) {
  const topics = {
    Python: {talk:'What is the difference between a list and a tuple, and when would you use each?',code:'Write a Python function that returns the first character in a string that appears only once.'},
    SQL: {talk:'When would you use a LEFT JOIN instead of an INNER JOIN?',code:'Write a SQL query to find the second-highest salary in an Employees table.'},
    'AI / ML': {talk:'How would you explain the difference between supervised and unsupervised learning?',code:'Write pseudocode for splitting a dataset into training and validation sets.'},
    'Full stack': {talk:'What happens between submitting a form and seeing the response in a web app?',code:'Write a small function that validates an email address before a form is submitted.'},
    OOP: {talk:'Can you explain encapsulation and when it is useful?',code:'Design a small class for a bank account and describe its key methods.'},
    JavaScript: {talk:'What is the difference between let, const, and var?',code:'Write a JavaScript function that removes duplicate values from an array.'}
  };
  const pair=topics[interview.topic]||{talk:`Which core idea in ${interview.topic} do you find most useful, and why?`,code:`Describe an algorithm or write a small solution for a practical ${interview.topic} problem.`};
  const coding=interview.interviewMode==='Coding & problem solving'||(interview.interviewMode==='Balanced'&&interview.number%2===0);
  const text=interview.interviewMode==='Technical conversation'?pair.talk:(coding?pair.code:pair.talk);
  return {text,isPractical:interview.interviewMode==='Technical conversation'?false:coding};
}

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
      current={topic:String(body.interview_type||'Python'),limit:Math.max(1,Math.min(50,Number(body.max_questions)||5)),number:1,answers:[],difficulty:body.difficulty||'Intermediate',interviewMode:body.interview_mode||'Balanced',sawPractical:false};
      const first=questionFor(current);current.sawPractical=first.isPractical;
      return send(res,200,{question_number:1,max_questions:current.limit,question:first.text,interview_completed:false});
    }
    if (req.method==='POST' && url.pathname==='/interview/answer') {
      const body=await readBody(req);
      if(!current)return send(res,404,{detail:'No active interview.'});
      current.answers.push(String(body.answer||''));
      if(current.number>=current.limit){
        const score=Math.min(9.6,Math.max(5.8,6.2+current.answers.reduce((n,a)=>n+Math.min(a.trim().length,160)/220,0))).toFixed(1);
        const report={interview_type:current.topic,knowledge_score:Number(score),problem_solving_score:current.sawPractical?Number(score):null,overall_score:Number(score),strengths:['You shared your reasoning clearly.','You stayed engaged throughout the practice.'],weaknesses:['A couple of answers could use more detail.'],areas_to_improve:['Add a specific example to support your key points.','Pause briefly to structure longer answers.'],overall_feedback:'A thoughtful practice. Your answers showed curiosity and a solid foundation. With a little more detail and a concrete example or two, you’ll make an even stronger impression.'};
        current=null;
        return send(res,200,{evaluation:'Interview completed.',interview_completed:true,report});
      }
      current.number++;
      const next=questionFor(current);current.sawPractical=current.sawPractical||next.isPractical;
      return send(res,200,{evaluation:'Thanks for sharing that. Let’s explore one more angle.',question_number:current.number,max_questions:current.limit,question:next.text,interview_completed:false});
    }
    if(req.method==='POST'&&url.pathname==='/interview/finish'){
      if(!current)return send(res,404,{detail:'No active interview.'});
      const topic=current.topic,practical=current.sawPractical;current=null;
      return send(res,200,{interview_type:topic,knowledge_score:7,problem_solving_score:practical?7:null,overall_score:7,strengths:['You made a good start.'],weaknesses:['Try adding more detail.'],areas_to_improve:['Use a concrete example.'],overall_feedback:'Thanks for practicing today.'});
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
server.on('error',error=>{
  if(error.code!=='EADDRINUSE'){
    console.error(error);
    process.exitCode=1;
    return;
  }

  const address=`http://127.0.0.1:${port}`;
  http.get(address,res=>{
    let body='';
    res.setEncoding('utf8');
    res.on('data',chunk=>body+=chunk);
    res.on('end',()=>{
      if(res.statusCode===200&&body.includes('COGNIV AI')){
        console.log(`Cogniv AI preview is already running: ${address}`);
      }else{
        console.error(`Port ${port} is already in use. Set PORT to another port and try again.`);
        process.exitCode=1;
      }
    });
  }).on('error',()=>{
    console.error(`Port ${port} is already in use. Set PORT to another port and try again.`);
    process.exitCode=1;
  });
});
server.listen(port,'127.0.0.1',()=>console.log(`Cogniv AI UI demo: http://127.0.0.1:${port}`));
