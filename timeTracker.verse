
using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }
using { /Fortnite.com/Characters }
using { /Verse.org/Verse } 
using { /Fortnite.com/Playspaces }

# Persistent player data (Key: player, Value: total play time in seconds)
var PlayerPlaytime:weak_map(player, float) = map{}


timeTracker := class(creative_device):
    ##############################################################
    ##### Copyright SupportYourCreator. All Rights Reserved. #####
    ##############################################################
    ##### Contact SupportYourCreator for licensing options.  #####
    ##### E-Mail: team@supportyourcreator.com                #####
    ##### Website: supportyourcreator.com                    #####
    ##############################################################

    var SECRET_KEY : int = 13456789012345679  # Your secret key here
    var public_key : int = 905712 # Your public key here

    # Button Device for triggering the message. You need to create a Button device manually in UEFN and link it to the timeTracker device.
    @editable
    Button : button_device = button_device{}

    # HUD Message Device for displaying time played. You need to create a HUD Message device manually in UEFN and linked it to the timeTracker device.
    @editable
    PopUpDialog : popup_dialog_device = popup_dialog_device{}  # Fullscreen message
    
    # Track when players join the game
    var PlayerStartTime:weak_map(player, float) = map{}

    OnBegin<override>()<suspends>:void =

        # Subscribe to Button Pressed Event
        Button.InteractedWithEvent.Subscribe(OnButtonPressed)
        Print("Subscribed to Button Pressed Event")

        # Track when players join the game
        Playspace := GetPlayspace()
        Playspace.PlayerAddedEvent().Subscribe(OnPlayerJoin)
        Print("Subscribed to Player Added Event")

        # Call OnPlayerJoin() manually for all players already in the game
        ExistingPlayers := Playspace.GetPlayers()
        for (Player : ExistingPlayers):
            Print("Following player is already in the game:")
            PrintPlayerName(Player)
            Print("Persisten storage played time:")
            if (TimeStored := PlayerPlaytime[Player]): 
                Print(ToString(TimeStored))
            else:
                Print("No stored data found")
            OnPlayerJoin(Player)

            Print("Persistent storage played time AFTERWARDS:")
            if (TimeStored := PlayerPlaytime[Player]): 
                Print(ToString(TimeStored))

     # Event triggered when a player joins the game
    OnPlayerJoin(Player: player):void =
        Print("Player Joined:")
        PrintPlayerName(Player)

        StartTime : float = GetSecondsSinceEpoch() # Get the current Unix time
        if:
            true  # always reset start time when player joins
            set PlayerStartTime[Player] = StartTime
        
        # Initialize playtime if the player is new
        if:
            not PlayerPlaytime[Player]
            set PlayerPlaytime[Player] = 0.0

        PrintPlayerName(Player)

    # Event function to handle button press
    OnButtonPressed(Agent : agent):void =
        if (Player := player[Agent]):  # Ensure the agent is a player
            if (StartTime := PlayerStartTime[Player]): # check if player has a start time
                CurrentTime : float = GetSecondsSinceEpoch()
                Print("Current Time is: " + ToString(CurrentTime))
                SessionDuration : float = CurrentTime - StartTime

                # Update the total playtime
                if (TotalTime := PlayerPlaytime[Player]):
                    if:
                        true  # Add the session duration to the total playtime
                        set PlayerPlaytime[Player] = TotalTime + SessionDuration
                else:
                    if:
                        true  # Initialize the total playtime
                        set PlayerPlaytime[Player] = SessionDuration
                
                
                if:
                    true  # Reset start time to prevent duplicate additions
                    set PlayerStartTime[Player] = CurrentTime

                # Convert time to minutes and seconds for readability
                if (TimePlayed := PlayerPlaytime[Player]):
                    if (Minutes := Ceil[TimePlayed / 60.0]):#Ceil[TimePlayed / 60.0]):  I changed it to seconds for testing
                        Print("Total Playtime is " + ToString(Minutes) + " for Player:")
                        PrintPlayerName(Player)

                        HashValue : message = IntToMessage(ComputeProofHash(public_key, Minutes))

                        

                        # 🔹 Configure Pop-Up Dialog
                        PopUpDialog.SetTitleText(StringToMessage("Take image & Upload to Discord!"))
                        PopUpDialog.SetDescriptionText(create_popup_message(Player, Minutes, HashValue, public_key))
                        PopUpDialog.SetButtonCount(1)  # Only one button: "Done"
                        PopUpDialog.SetButtonText(StringToMessage("Done"), 0)


                        # 📢 Show Pop-Up
                        PopUpDialog.Show(Player)

                        Print("✔ Pop-up Displayed")

                        # Resume when the player presses "Done"
                        PopUpDialog.RespondingButtonEvent.Subscribe(OnDialogClosed)

                Print("Persistent storage played time AFTERWARDS PRESSBUTTON:")
                if (TimeStored := PlayerPlaytime[Player]): 
                    Print(ToString(TimeStored))

                        
            
            else:
                Print("Player start time not found")
        
        else:
            Print("Agent is not a player")
            


    create_popup_message<localizes>(Player: player, Minutes:int, HashValue: message, pub_key: int)<computes>:message=
        "Name: {Player} \n Hash: {pub_key}X{HashValue} \n Played Time (in minutes): {Minutes} \n\n Test: ツ	么	彡	〆	私٭	Ł	ॐ	×"




        
    # --- ENCRYPTION ---

    CharToIntMap : [char]int = map{
    'A' => 1, 'B' => 2, 'C' => 3, 'D' => 4, 'E' => 5, 'F' => 6, 'G' => 7, 'H' => 8, 'I' => 9,
    'J' => 10, 'K' => 11, 'L' => 12, 'M' => 13, 'N' => 14, 'O' => 15, 'P' => 16, 'Q' => 17, 'R' => 18,
    'S' => 19, 'T' => 20, 'U' => 21, 'V' => 22, 'W' => 23, 'X' => 24, 'Y' => 25, 'Z' => 26,
    '0' => 27, '1' => 28, '2' => 29, '3' => 30, '4' => 31, '5' => 32, '6' => 33, '7' => 34, '8' => 35, '9' => 36,
    '-' => 37, '_' => 38, '.' => 39, ' ' => 40 
    }


    ComputeProofHash(MapCode:int, PlayTime:int):int=
        var hash: int = -1
        if (hash_ := mod[((MapCode * 134569 + PlayTime * 456781) + SECRET_KEY), 3456789]):
            set hash = hash_
        hash



        
    mod(a: int, b: int)<decides><transacts>: int =
        mod_result: int = a - (Floor(a / b) * b)


    
    # --- END OF ENCRYPTION ---







    

    GetAgentName<localizes>(Agent:agent)<computes>: message = "{Agent}"
    GetPlayerName<localizes>(Player:player)<computes>: message = "{Player}"
    StringToMessage<localizes>(value:string) : message = "{value}"
    IntToMessage<localizes>(value:int) : message = "{value}"

    PrintPlayerName(Player:player):void=
        Username : message = GetPlayerName(Player)
        Print(Username)
    
    PrintAgentName(Agent:agent):void=
        Username : message = GetAgentName(Agent)
        Print(Username)
          
    OnDialogClosed(Agent: agent, ButtonIndex: int):void =
        Print("✔ Player closed the pop-up and gameplay resumes.")