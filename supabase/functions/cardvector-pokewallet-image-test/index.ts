import { createClient } from "npm:@supabase/supabase-js@2";
const SUPABASE_URL=Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_ANON_KEY=Deno.env.get("SUPABASE_ANON_KEY") || "";
const allowed=new Map<string,string>([
 ["heracross","pk_82d00c11b3458867cbc585fe20a5f75de34edf3271244713db31ced8ec8f9d3bd94baf2b65bca37b87615a45f58a"],
 ["steelix","pk_90de54fb9cf724d43772b6c2b2c68c5452019ab32015f4fab4c6a264a470fdc563b0263e89680d7bbe0a4141224efa"],
 ["rayquaza","pk_520c7aa5698ed70f1c6b4186f59eaf94e9c2c5c4a54cd80c3e9898493579428bca79862a44270246fcaa957350d6e44b"]
]);
const cache=new Map<string,{expires:number,data:ArrayBuffer}>();
const cors={"Access-Control-Allow-Origin":"https://cardvector.app","Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"authorization,apikey,x-client-info,content-type","Vary":"Origin"};
const json=(message:string,status:number)=>new Response(JSON.stringify({error:message}),{status,headers:{...cors,"Content-Type":"application/json","Cache-Control":"no-store"}});
Deno.serve(async req=>{
 if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors});
 if(req.method!=="POST")return json("POST required",405);
 const authorization=req.headers.get("Authorization")||"";
 if(!authorization.startsWith("Bearer "))return json("Sign in required",401);
 if(!SUPABASE_URL||!SUPABASE_ANON_KEY)return json("Account service unavailable",503);
 const client=createClient(SUPABASE_URL,SUPABASE_ANON_KEY,{auth:{persistSession:false}});
 const {data:{user},error}=await client.auth.getUser(authorization.slice(7));
 if(error||!user)return json("Sign in required",401);
 if(user.email?.toLowerCase()!=="jhill2487@gmail.com"||!user.email_confirmed_at)return json("Administrator only",403);
 const body=await req.json().catch(()=>null);
 const card=typeof body?.card==="string"?body.card:"";
 const providerId=allowed.get(card);
 if(!providerId)return json("Image not enabled for this card",404);
 const now=Date.now();
 let image=cache.get(card);
 if(!image||image.expires<now){
  const secret=Deno.env.get("POKEWALLET_API_KEY");
  if(!secret)return json("Image service not configured",503);
  try {
   const result=await fetch("https://api.pokewallet.io/images/"+providerId+"?size=low",{headers:{"X-API-Key":secret},signal:AbortSignal.timeout(15000)});
   if(!result.ok)return json(result.status===429?"Image rate limit reached":"Image unavailable",result.status===429?429:502);
   const data=await result.arrayBuffer();
   // PokéWallet currently reports image/jpeg for PNG bytes; validate and correct MIME.
   const header=new Uint8Array(data.slice(0,24));
   const png=header.length===24&&[137,80,78,71,13,10,26,10].every((byte,index)=>header[index]===byte);
   if(!png||data.byteLength<256||data.byteLength>1000000)return json("Unexpected image response",502);
   const view=new DataView(data);
   const width=view.getUint32(16),height=view.getUint32(20);
   if(width<100||width>2000||height<100||height>3000)return json("Invalid image dimensions",502);
   image={data,expires:now+8*60*60*1000};
   if(cache.size>=3)cache.delete(cache.keys().next().value!);
   cache.set(card,image);
  }catch{return json("Image retrieval failed",502);}
 }
 return new Response(image.data.slice(0),{status:200,headers:{...cors,"Content-Type":"image/png","Cache-Control":"private, max-age=3600","X-Content-Type-Options":"nosniff"}});
});
