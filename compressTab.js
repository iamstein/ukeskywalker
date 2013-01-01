function getLineType(s) { // categorizes line as "blank", "chord" or "lyrics". 

 if (s.length==0) {
  return "blank"
 }
 
 //count the number of white spaces and compute white space fraction
  var NumWhiteSpace = 0;
  for (var i=0; i<s.length; i++) {
   if (s[i] == " " || s[i] == "\t") {
    NumWhiteSpace++
   }
  }
  var WhiteSpaceFraction = NumWhiteSpace/s.length;
  
 // check line to see if it contains chords
  var Chords = s.match(/\b[A-G][b#]?[m\d]*(sus)?(dim)?\d*\b/);
     
 //return categorization based on number of white spaces
  if (WhiteSpaceFraction==1)
   return "blank"
  //else if (WhiteSpaceFraction > 0.5) {
  else if (Chords != null)
   return "chords"
  else
   return "lyrics"
}  

function mergeChordsWithLyrics(chords,lyrics) {
 
 // Create an arrays of chord names (crd) and positons (pos)
  var crd = new Array; // chord name
  var pos = new Array; // chord position
  for (var i=0; i<chords.length; i++) {  
   if (chords.charAt(i) != " " && chords.charAt(i) != "\t") {   
    if (i==0) { //create new chord 
     crd.push(chords.charAt(i));
     pos.push(i); 
    }
    else if (chords.charAt(i-1) == " " && chords.charAt(i) != "\t") { //create new chord
     crd.push(chords.charAt(i));
     pos.push(i);
    }   
    else { //add on to last chord
     crd[crd.length-1] = crd[crd.length-1] + chords.charAt(i);
    }
   }  
  }
  // THIS PART DISPLAYS THE CHORDS AS A CHECK
  /*
  var test = "";
  for (var i=0; i<crd.length; i++) {
   test = test + crd[i] + "-" + pos[i] + "\n";
  }
  alert(test);
  */
  
 // interleave chords into lyrics
  var s = lyrics;
  var j
  
  for (var i=crd.length-1; i>=0; i--) {
   // go backwards from chord until you find white space or the beginning of the line
   j = pos[i];
   while (j>=0 && lyrics.charAt(j) != " " && lyrics.charAt(j) != "\t") {
    j--;
   }
   s = s.substring(0,j) + " [" + crd[i] + "] " + s.substring(j,s.length);
  }
  
 // remove the extra spaces
  s = s.replace( /[\s\n\r]+/g, ' ' );
  if (s[0] == " " || s[0] == "\t") {
   s = s.substring(1,s.length)
  }
  
 return s;
}

function compressTab() {
 // read input tab
  var s = document.getElementById("TabInput").value;

 // compute line category for each line 
  var s = s.split("\n");
  var s_type = new Array;
  for (var i=0; i<s.length; i++) {
   s_type[i] = getLineType(s[i]);
  }
  
  //alert(s_type)
  
 // create merged output
 // loop through lines.  
 // any time there's a chord line followed by a lyrics line, merge the two together in the output
  var s_output = ""
  for (var i=0; i<s.length; i++) {
   if (s_type[i] == "lyrics") {
    s_output = s_output + s[i]+"\n"
   }
   else if (s_type[i] == "chords") {
    if (i==s.length) {
     s_output = s_output + s[i];
    }
    else {
     if (s_type[i+1]=="lyrics") {
      s_output = s_output + mergeChordsWithLyrics(s[i],s[i+1]) + "\n";
      i++; //skip the next line
     }
     else {
      s_output = s_output + s[i] + "\n";
     }     
    }
   }
   else if (s_type[i] == "blank") {
    s_output = s_output + "\n";
   }
  }
  
 // output the tab
  //var s_output = s_linetype;
  document.getElementById("TabOutput").value = s_output;
 }