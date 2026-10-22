"""Name and city pools for the seed generators.

Each country has large first-name and last-name pools so that tens of thousands of people can
all have DIFFERENT full names ("First Last", no middle names). Capacity per country is
len(first) x len(last); `unique_person` raises a clear error if you ask for more people than
the pools can supply instead of looping forever.
"""

import random


def _pool(text: str) -> list[str]:
    """Comma-separated names -> list, preserving order and dropping duplicates."""
    return list(
        dict.fromkeys(part.strip() for part in text.replace("\n", " ").split(",") if part.strip())
    )


NAMES = {
    "IN": (
        _pool("""Aarav, Aditya, Advik, Arjun, Atharv, Ayaan, Dhruv, Ishaan, Kabir, Krish, Reyansh, Rohan, Sai, Vihaan, Vivaan, Yash,
        Aryan, Karan, Rahul, Rishi, Siddharth, Nikhil, Varun, Manish, Harsh, Dev, Kartik, Vikram, Amit, Ankit, Gaurav, Mohit,
        Pranav, Tushar, Naveen, Suresh, Ramesh, Rajesh, Sanjay, Anil, Vijay, Deepak, Pankaj, Sachin, Rohit, Abhishek, Akash,
        Ashish, Bharat, Chetan, Darshan, Eshan, Girish, Hemant, Jatin, Kunal, Lalit, Mayank, Nitin, Omkar, Prateek, Rajat,
        Sameer, Tarun, Uday, Vedant, Yogesh, Zubin, Ananya, Aadhya, Aanya, Diya, Isha, Kavya, Meera, Myra, Neha, Pari, Priya,
        Riya, Saanvi, Shreya, Tanvi, Anika, Anjali, Bhavna, Charvi, Disha, Esha, Gauri, Harini, Ira, Jahnavi, Kiara, Lakshmi,
        Mahika, Nandini, Pooja, Radhika, Sakshi, Tanya, Uma, Vaishnavi, Yamini, Zoya, Aditi, Divya, Ishita, Juhi, Kriti, Mansi,
        Nisha, Palak, Rashmi, Shruti, Swati, Trisha, Vandana, Sneha, Pallavi, Rekha, Sunita, Anita, Kavita, Meenal, Sonal, Rupal"""),
        _pool("""Sharma, Iyer, Mehta, Reddy, Singh, Kulkarni, Nair, Menon, Rao, Gupta, Patel, Joshi, Desai, Banerjee, Chatterjee,
        Mukherjee, Das, Bose, Sen, Ghosh, Roy, Dutta, Saha, Pillai, Krishnan, Subramanian, Venkatesh, Naidu, Shetty, Hegde, Bhat,
        Kamath, Pai, Shenoy, Kapoor, Khanna, Malhotra, Chopra, Arora, Bhatia, Sethi, Verma, Mishra, Pandey, Tiwari, Dubey, Shukla,
        Yadav, Chauhan, Rathore, Thakur, Jain, Agarwal, Bansal, Goel, Mittal, Saxena, Srivastava, Nanda, Bajaj, Ahluwalia, Gill,
        Sandhu, Dhillon, Grewal, Sidhu, Ansari, Khan, Qureshi, Siddiqui, Sheikh, Mirza, Fernandes, Pereira, Gomes, Lobo, Pinto,
        Menezes, Rodrigues, Thomas, Mathew, Joseph, George, Varghese, Abraham, Kurian, Patil, Deshmukh, Jadhav, Pawar, Shinde,
        More, Gaikwad, Chavan, Kale, Bhosale, Wagh, Bhide, Apte, Phadke, Sathe, Kelkar, Gokhale, Karnik, Pradhan, Mohanty,
        Behera, Panda, Nayak, Mahapatra, Rout, Barman, Hazarika, Gogoi, Borah, Naik, Gaonkar, Prabhu, Rajan, Narayanan,
        Ramachandran, Swaminathan, Balasubramanian, Chandran, Kumar, Murthy, Gowda, Shah, Modi, Trivedi, Parekh, Thakkar"""),
    ),
    "US": (
        _pool("""James, Emily, Michael, Olivia, Daniel, Sophia, Ethan, Ava, William, Isabella, Benjamin, Mia, Lucas, Charlotte, Henry,
        Amelia, Alexander, Harper, Jackson, Evelyn, Sebastian, Abigail, Jack, Ella, Owen, Scarlett, Samuel, Grace, Matthew, Chloe,
        Joseph, Victoria, Levi, Riley, David, Aria, Wyatt, Lily, Carter, Aurora, Julian, Zoey, Luke, Penelope, Grayson, Layla,
        Isaac, Nora, Lincoln, Hazel, Anthony, Luna, Hudson, Ellie, Dylan, Stella, Ezra, Paisley, Thomas, Violet, Charles, Lucy,
        Christopher, Claire, Jaxon, Skylar, Maverick, Madison, Josiah, Savannah, Andrew, Brooklyn, Elijah, Bella, Joshua, Leah,
        Nathan, Audrey, Aaron, Eleanor, Eli, Naomi, Landon, Caroline, Hunter, Genesis, Connor, Alice, Adrian, Sadie, Jeremiah, Hailey"""),
        _pool("""Carter, Brooks, Nguyen, Rivera, Walker, Bennett, Hayes, Foster, Smith, Johnson, Williams, Brown, Jones, Garcia, Miller,
        Davis, Rodriguez, Martinez, Hernandez, Lopez, Gonzalez, Wilson, Anderson, Thomas, Taylor, Moore, Jackson, Martin, Lee,
        Perez, Thompson, White, Harris, Sanchez, Clark, Ramirez, Lewis, Robinson, Young, Allen, King, Wright, Scott, Torres, Hill,
        Flores, Green, Adams, Nelson, Baker, Hall, Campbell, Mitchell, Roberts, Phillips, Evans, Turner, Parker, Collins, Edwards,
        Stewart, Morris, Murphy, Cook, Rogers, Morgan, Cooper, Peterson, Reed, Bailey, Bell, Gomez, Kelly, Howard, Ward, Cox, Diaz,
        Richardson, Wood, Watson, Gray, James, Reyes, Cruz, Hughes, Price, Myers, Long, Sanders, Ross, Morales, Powell, Sullivan,
        Russell, Ortiz, Jenkins, Gutierrez, Perry, Butler, Barnes, Fisher"""),
    ),
    "GB": (
        _pool("""Oliver, Amelia, Harry, Isla, George, Freya, Arthur, Poppy, Noah, Ivy, Jack, Willow, Leo, Evie, Oscar, Rosie, Charlie,
        Daisy, Archie, Phoebe, Alfie, Sienna, Henry, Matilda, Theo, Florence, Thomas, Ruby, Freddie, Elsie, Jacob, Emily, Edward,
        Eliza, Joshua, Lily, Samuel, Grace, Harrison, Erin, Max, Maisie, Lucas, Millie, Albert, Esme, Ethan, Bonnie, Isaac, Alice,
        Finley, Sophie, Mason, Imogen, Louie, Thea, Reggie, Harriet, Jude, Maya, Elliot, Elodie, Hugo, Callum, Niamh, Rory, Orla,
        Fraser, Eilidh, Angus, Morven, Gethin, Cerys"""),
        _pool("""Whitfield, Hughes, Clarke, Ashworth, Thornton, Doyle, Fletcher, Gray, Smith, Jones, Taylor, Brown, Williams, Wilson,
        Johnson, Davies, Robinson, Wright, Thompson, Evans, Walker, White, Roberts, Green, Hall, Wood, Jackson, Harrison, Bennett,
        Hill, Cooper, Turner, Parker, Edwards, Carter, Mitchell, Shaw, Ward, Watson, Ellis, Palmer, Bailey, Marshall, Lawrence,
        Barker, Cole, Knight, Hunt, Holmes, Pearce, Chapman, Burton, Fox, Hudson, Murray, MacDonald, Campbell, Stewart, Reid, Kerr,
        Morgan, Griffiths, Price, Rees, Pritchard, Lloyd, Owen, Gallagher, Murphy, Kelly, Byrne"""),
    ),
    "DE": (
        _pool("""Lukas, Mia, Felix, Hannah, Jonas, Lea, Maximilian, Clara, Leon, Emilia, Paul, Sophia, Finn, Emma, Elias, Lina, Noah,
        Marie, Luis, Anna, Ben, Johanna, Henry, Charlotte, Anton, Ida, Moritz, Greta, Niklas, Frieda, Jan, Lotte, Tim, Nele, Julian,
        Mila, Simon, Laura, Tobias, Julia, Fabian, Sarah, David, Katharina, Samuel, Lara, Philipp, Jana, Florian, Lisa, Matthias,
        Nina, Stefan, Eva, Sebastian, Carla, Markus, Theresa, Daniel, Pia, Kilian"""),
        _pool("""Schneider, Weber, Fischer, Becker, Hoffmann, Keller, Richter, Wolf, Müller, Schmidt, Meyer, Wagner, Schulz, Koch,
        Bauer, Klein, Schröder, Neumann, Schwarz, Zimmermann, Braun, Krüger, Hofmann, Hartmann, Lange, Schmitt, Werner, Krause,
        Meier, Lehmann, Schmid, Schulze, Maier, Köhler, Herrmann, König, Walter, Mayer, Huber, Kaiser, Fuchs, Peters, Lang, Scholz,
        Möller, Weiß, Jung, Hahn, Schubert, Vogel, Friedrich, Günther, Frank, Berger, Winkler, Roth, Beck, Lorenz, Baumann, Franke, Albrecht"""),
    ),
    "FR": (
        _pool("""Louis, Camille, Hugo, Chloé, Jules, Manon, Léa, Théo, Gabriel, Emma, Raphaël, Louise, Arthur, Alice, Lucas, Jade, Adam,
        Lina, Nathan, Rose, Ethan, Anna, Leo, Mia, Tom, Inès, Noé, Léna, Maël, Zoé, Paul, Juliette, Mathis, Sarah, Enzo, Eva, Timéo,
        Clara, Nolan, Lola, Samuel, Margaux, Victor, Charlotte, Clément, Agathe, Antoine, Romane, Maxime, Océane, Baptiste, Élise,
        Pierre, Mathilde, Quentin, Pauline, Romain, Marion"""),
        _pool("""Dubois, Moreau, Laurent, Lefèvre, Girard, Bonnet, Fontaine, Mercier, Martin, Bernard, Thomas, Petit, Robert, Richard,
        Durand, Leroy, Simon, Michel, Garcia, David, Bertrand, Roux, Vincent, Fournier, Morel, André, Lambert, Rousseau, Blanc,
        Guerin, Muller, Henry, Roussel, Nicolas, Perrin, Morin, Mathieu, Clement, Gauthier, Dumont, Lopez, Chevalier, Robin, Masson,
        Sanchez, Gerard, Nguyen, Boyer, Denis, Lemaire, Duval, Joly, Gautier, Roger, Roche, Roy, Noel, Meyer, Lucas, Meunier, Jean"""),
    ),
    "AE": (
        _pool("""Omar, Layla, Khalid, Noor, Yusuf, Mariam, Tariq, Salma, Ahmed, Fatima, Mohammed, Aisha, Ali, Huda, Hassan, Zainab,
        Ibrahim, Amira, Hamza, Lina, Zayed, Maryam, Saeed, Reem, Rashid, Sara, Majid, Dana, Faisal, Hind, Nasser, Yasmin, Sultan,
        Rania, Adel, Nadia, Karim, Leila, Bilal, Samira, Jamal, Farah, Walid, Dalia, Samir, Mona, Rami, Jana, Anwar, Hala, Fadi,
        Lubna, Imran, Ayesha, Rohan, Priya, Arjun, Neha, Vikram, Kavya, Sanjay, Anita, Rahul, Divya, Faraz, Sana"""),
        _pool("""Al Mansoori, Al Suwaidi, Al Falasi, Al Mazrouei, Al Shamsi, Al Kaabi, Al Marri, Al Dhaheri, Al Zaabi, Al Hashimi,
        Haddad, Khoury, Nasser, Farouk, Saleh, Mansour, Hamdan, Jaber, Darwish, Habib, Aziz, Rahman, Siddiqui, Qureshi, Malik,
        Chaudhry, Sheikh, Hussain, Khan, Ansari, Iyer, Menon, Nair, Pillai, Sharma, Mehta, Gupta, Kapoor, Fernandes, Costa, Rizvi,
        Bukhari, Naqvi, Zaidi, Abbasi, Mirza, Baig, Hashmi, Sayed, Qasim, Yousuf, Tahir, Anwar, Javed, Shah, Bhatti"""),
    ),
    "SG": (
        _pool("""Wei Jie, Mei Ling, Jun Hao, Hui Min, Kai Xiang, Shu Ting, Zhi Wei, Xin Yi, Jia Hao, Jia Wen, Zi Xuan, Yi Xuan,
        Ming Jun, Li Ting, Wen Hui, Yong Sheng, Jun Jie, Pei Shan, Rui En, Hui Ling, Zheng Hao, Si Min, Kai Wen, Xiu Ling, Jing Yi,
        Cheng Wei, Yu Xuan, Min Hui, Zhi Hao, Yi Ling, Aaron, Daniel, Joshua, Rachel, Sarah, Natalie, Ryan, Jonathan, Priya,
        Arjun, Kavitha, Rajesh, Siti, Nurul, Aisyah, Muhammad, Ahmad, Farah, Hafiz, Amirah, Raj, Anita, Deepa, Vikram, Sanjay,
        Meera, Kumar, Selvi"""),
        _pool("""Tan, Lim, Lee, Ng, Chua, Goh, Teo, Ong, Wong, Chan, Koh, Yeo, Sim, Ho, Chong, Low, Toh, Foo, Seah, Heng, Quek, Phua,
        Soh, Ang, Loh, Lau, Chew, Yap, Leong, Neo, Kwok, Ow, Pang, Tay, Wee, Singh, Nair, Pillai, Kumar, Rahman, Abdullah, Ismail,
        Hassan, Yusof, Rahim, Menon, Krishnan, Raj, Devi, Subramaniam, Gopal"""),
    ),
    "AU": (
        _pool("""Jack, Charlotte, Noah, Grace, Liam, Ruby, Lachlan, Zoe, Oliver, Olivia, William, Mia, Thomas, Amelia, Henry, Isla,
        Ethan, Ava, Mason, Chloe, Lucas, Harper, Cooper, Matilda, Archie, Evie, Hudson, Sienna, Hunter, Willow, Riley, Lily, Max,
        Sophie, Leo, Ella, Harry, Georgia, Jacob, Hannah, Oscar, Emily, Alexander, Isabelle, Joshua, Scarlett, Jaxon, Stella,
        Harrison, Billie, Samuel, Frankie, Angus, Poppy, Flynn, Eliza, Beau, Tilly, Xavier, Piper"""),
        _pool("""Mitchell, Harrison, Campbell, Sullivan, Murray, Fraser, Gibson, Reid, Smith, Jones, Williams, Brown, Wilson, Taylor,
        Johnson, White, Martin, Anderson, Thompson, Nguyen, Thomas, Walker, Harris, Lee, Ryan, Robinson, Kelly, King, Davis, Wright,
        Evans, Roberts, Green, Hall, Wood, Jackson, Clarke, Turner, Hill, Scott, Moore, Cooper, Ward, Morris, Watson, Baker, Cook,
        Hughes, Russell, Bell, Palmer, Shaw, Mills, Fleming, Stewart, Henderson, Ross, Hunter, Webb, Douglas, Marshall"""),
    ),
    "CA": (
        _pool("""Logan, Emma, Mason, Chloe, Ryan, Sophie, Lucas, Ella, Liam, Olivia, Noah, Charlotte, Ethan, Ava, Benjamin, Sophia,
        Jacob, Amelia, Nathan, Zoe, Gabriel, Léa, Samuel, Alice, Felix, Emilie, Antoine, Florence, Thomas, Jade, Alexis, Camille,
        William, Mia, Owen, Hannah, Dylan, Emily, Carter, Avery, Hudson, Harper, Jaxon, Nora, Parker, Layla, Tyler, Stella, Connor,
        Grace, Evan, Maya, Aiden, Sarah, Ravi, Priya, Jasmine, Arjun, Wei, Mei, Hassan, Fatima, Jin, Ying, Amir, Sara"""),
        _pool("""Tremblay, Gagnon, Roy, MacDonald, Wong, Bouchard, Singh, Fraser, Smith, Brown, Lee, Wilson, Martin, Campbell, Anderson,
        Taylor, Thompson, White, Clark, Stewart, Murphy, Cote, Gauthier, Morin, Lavoie, Fortin, Gagne, Ouellet, Pelletier, Belanger,
        Levesque, Bergeron, Leblanc, Paquette, Girard, Simard, Boucher, Lapointe, Nguyen, Chen, Li, Wang, Zhang, Liu, Patel, Sharma,
        Gill, Sidhu, Khan, Ahmed, Ali, Hussain, Kaur, Dhillon, Grewal, Sandhu, Johal, Brar, Mann, Cheung, Lam, Chan, Yang, Kim, Park"""),
    ),
    "BR": (
        _pool("""Lucas, Gabriela, Mateus, Beatriz, Rafael, Larissa, Thiago, Camila, Gabriel, Maria, Pedro, Ana, Miguel, Julia, Arthur,
        Laura, Heitor, Manuela, Davi, Alice, Bernardo, Valentina, Theo, Helena, Lorenzo, Isabella, Matheus, Luiza, Gustavo, Sophia,
        Felipe, Giovanna, Bruno, Leticia, Henrique, Fernanda, Guilherme, Amanda, Rodrigo, Bianca, Leonardo, Clara, Caio, Mariana,
        Vinicius, Rafaela, Daniel, Carolina, Andre, Isadora, Joao, Eduarda, Diego, Yasmin, Victor, Livia"""),
        _pool("""Silva, Santos, Oliveira, Souza, Costa, Pereira, Almeida, Ribeiro, Rodrigues, Ferreira, Alves, Lima, Gomes, Martins,
        Araujo, Carvalho, Melo, Barbosa, Rocha, Dias, Nunes, Moreira, Cardoso, Teixeira, Correia, Cavalcanti, Machado, Freitas,
        Moura, Pinto, Campos, Monteiro, Castro, Azevedo, Mendes, Barros, Ramos, Vieira, Lopes, Fernandes, Cunha, Duarte, Miranda,
        Nascimento, Marques, Batista, Medeiros, Fonseca, Peixoto, Andrade, Tavares, Borges, Coelho, Siqueira, Xavier, Guimaraes, Brito"""),
    ),
}

# Real cities, most populous first (earlier cities are picked more often).
CITIES = {
    "IN": _pool(
        "Mumbai, Delhi, Bengaluru, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad, Jaipur, Kochi, Lucknow, Indore, Chandigarh, Nagpur, Coimbatore, Surat"
    ),
    "US": _pool(
        "New York, Los Angeles, Chicago, Houston, Phoenix, Seattle, Boston, Austin, Denver, Atlanta, San Francisco, Miami, Dallas, Philadelphia"
    ),
    "GB": _pool(
        "London, Manchester, Birmingham, Leeds, Glasgow, Bristol, Edinburgh, Liverpool, Sheffield, Cardiff"
    ),
    "DE": _pool(
        "Berlin, Hamburg, Munich, Cologne, Frankfurt, Stuttgart, Düsseldorf, Leipzig, Dresden"
    ),
    "FR": _pool("Paris, Marseille, Lyon, Toulouse, Nice, Nantes, Bordeaux, Lille, Strasbourg"),
    "AE": _pool("Dubai, Abu Dhabi, Sharjah, Ajman, Ras Al Khaimah"),
    "SG": _pool("Singapore"),
    "AU": _pool("Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Gold Coast"),
    "CA": _pool("Toronto, Montreal, Vancouver, Calgary, Ottawa, Edmonton, Winnipeg"),
    "BR": _pool(
        "São Paulo, Rio de Janeiro, Brasília, Salvador, Belo Horizonte, Curitiba, Fortaleza, Recife"
    ),
}


def pick_city(rng: random.Random, country: str) -> str:
    """A city for the country; bigger cities (listed first) are more likely."""
    cities = CITIES[country]
    return rng.choices(cities, weights=range(len(cities), 0, -1))[0]


def unique_person(rng: random.Random, country: str, taken: set[str]) -> str:
    """A full name ("First Last") not yet in `taken`; adds it to `taken` and returns it."""
    firsts, lasts = NAMES[country]
    for _ in range(400):
        name = f"{rng.choice(firsts)} {rng.choice(lasts)}"
        if name not in taken:
            taken.add(name)
            return name
    raise SystemExit(
        f"Could not find an unused {country} name: lower --users or extend scripts/people_data.py"
    )
